const express = require("express");
const cors = require("cors");
const { spawn } = require("child_process");
const path = require("path");

const app = express();
const port = 3000;

// Pre-spawn Python process for faster responses
let pythonProcess = null;
let isProcessReady = false;
let pendingRequests = new Map();
let requestCounter = 0;

// 🔄 NEW: Environment detection
const isProduction = process.env.NODE_ENV === 'production' || process.env.DOCKER_ENV;
const isContainer = process.env.DOCKER_ENV === 'true' || process.env.PYTHONPATH === '/app/venv/bin';

console.log(`🔍 Environment: ${isProduction ? 'Production' : 'Development'}`);
console.log(`🔍 Container: ${isContainer ? 'Yes' : 'No'}`);

// CORS configuration - more restrictive in production
app.use(cors({
    origin: isProduction ? process.env.ALLOWED_ORIGINS?.split(',') || false : true,
    methods: ['GET', 'POST', 'OPTIONS'],
    allowedHeaders: ['Content-Type', 'Accept', 'Authorization', 'x-request-id'],
    credentials: false
}));

app.use(express.json({ limit: '1mb' }));

// Optimized request logging
app.use((req, res, next) => {
    if (req.path === '/chat') {
        console.log(`[${Date.now()}] CHAT REQUEST`);
    }
    next();
});

/**
 * 🔄 NEW: Get Python environment path based on container vs local setup
 */
function getPythonPath() {
    // Check environment variables first
    if (process.env.PYTHON_PATH) {
        return process.env.PYTHON_PATH;
    }
    
    // Container environment
    if (isContainer || isProduction) {
        return '/app/venv/bin/python';
    }
    
    // Local development - your existing path
    return '/Users/Apple/Documents/stages/Stage_StartNow/chatbot/.venv/bin/python';
}

/**
 * 🔄 NEW: Get script paths based on environment
 */
function getScriptPaths() {
    let baseDir;
    
    if (isContainer || isProduction) {
        // Container path
        baseDir = '/app/python';
    } else {
        // Local development path
        baseDir = path.join(__dirname, "../../Implementation");
    }
    
    return {
        persistentScript: path.join(baseDir, "src/chatbot_persistent.py"),
        fallbackScript: path.join(baseDir, "src/chatbot.py"),
        workingDir: baseDir
    };
}

/**
 * 🔄 UPDATED: Initialize persistent Python process for faster responses
 */
function initializePythonProcess() {
    const pythonPath = getPythonPath();
    const { persistentScript, fallbackScript, workingDir } = getScriptPaths();
    
    console.log(`🔍 Python path: ${pythonPath}`);
    console.log(`🔍 Working directory: ${workingDir}`);
    console.log(`🔍 Persistent script: ${persistentScript}`);
    console.log(`🔍 Fallback script: ${fallbackScript}`);
    
    // Check if persistent script exists
    const fs = require('fs');
    const scriptPath = fs.existsSync(persistentScript) ? persistentScript : fallbackScript;
    
    if (scriptPath === fallbackScript) {
        console.log("⚠️ Using fallback mode - persistent script not found");
        return; // Don't start persistent process, use fallback for all requests
    }
    
    console.log("🔄 Starting persistent Python process...");
    console.log(`📝 Using script: ${scriptPath}`);
    
    try {
        pythonProcess = spawn(pythonPath, [scriptPath], {
            cwd: workingDir,
            stdio: ['pipe', 'pipe', 'pipe'],
            env: {
                ...process.env,
                PYTHONPATH: workingDir,
                PYTHONUNBUFFERED: '1'
            }
        });

        let buffer = '';
        
        pythonProcess.stdout.on('data', (data) => {
            buffer += data.toString();
            
            // Process complete responses (assuming newline-delimited JSON)
            const lines = buffer.split('\n');
            buffer = lines.pop(); // Keep incomplete line in buffer
            
            lines.forEach(line => {
                if (line.trim()) {
                    // Check if the line looks like JSON before trying to parse
                    const trimmedLine = line.trim();
                    if (trimmedLine.startsWith('{') && trimmedLine.endsWith('}')) {
                        try {
                            const response = JSON.parse(trimmedLine);
                            handlePythonResponse(response);
                        } catch (e) {
                            console.error("Failed to parse Python JSON response:", trimmedLine);
                            console.error("Parse error:", e.message);
                        }
                    } else {
                        // Non-JSON line - log it but don't try to parse
                        console.log("Python stdout (non-JSON):", trimmedLine);
                    }
                }
            });
    });

        pythonProcess.stderr.on('data', (data) => {
            const error = data.toString();
            if (error.includes('READY')) {
                isProcessReady = true;
                console.log("✅ Python process ready");
            } else {
                console.error("Python stderr:", error);
            }
        });

        pythonProcess.on('close', (code) => {
            console.log(`❌ Python process closed with code ${code}`);
            isProcessReady = false;
            // Auto-restart on unexpected closure (with backoff)
            setTimeout(initializePythonProcess, 2000);
        });

        pythonProcess.on('error', (err) => {
            console.error("❌ Python process error:", err.message);
            isProcessReady = false;
        });
        
    } catch (error) {
        console.error("❌ Failed to spawn Python process:", error.message);
        isProcessReady = false;
    }
}

/**
 * Handle response from persistent Python process
 */
function handlePythonResponse(response) {
    const { requestId, result, error } = response;
    
    if (pendingRequests.has(requestId)) {
        const { resolve, reject } = pendingRequests.get(requestId);
        pendingRequests.delete(requestId);
        
        if (error) {
            reject(new Error(error));
        } else {
            resolve(result);
        }
    }
}

/**
 * Send message to persistent Python process
 */
function sendToPythonProcess(message, requestId) {
    return new Promise((resolve, reject) => {
        if (!pythonProcess || !isProcessReady) {
            return reject(new Error("Python process not ready"));
        }

        // Store request callbacks
        pendingRequests.set(requestId, { resolve, reject });
        
        // Set timeout (longer in production due to potential slower containers)
        const timeout = isProduction ? 30000 : 15000;
        setTimeout(() => {
            if (pendingRequests.has(requestId)) {
                pendingRequests.delete(requestId);
                reject(new Error("Request timeout"));
            }
        }, timeout);

        // Send request to Python process
        const request = JSON.stringify({
            requestId,
            message,
            timestamp: Date.now()
        }) + '\n';
        
        try {
            pythonProcess.stdin.write(request);
        } catch (error) {
            pendingRequests.delete(requestId);
            reject(new Error("Failed to write to Python process"));
        }
    });
}

/**
 * 🔄 UPDATED: Fallback function using your original chatbot.py script
 */
function handleLLMFallback(message, clientRequestId) {
    return new Promise((resolve, reject) => {
        const pythonPath = getPythonPath();
        const { fallbackScript, workingDir } = getScriptPaths();
        
        console.log(`🔄 Fallback using: ${pythonPath} ${fallbackScript}`);
        console.log(`🔄 Working directory: ${workingDir}`);
        
        try {
            const pythonProcess = spawn(pythonPath, [fallbackScript, message], {
                cwd: workingDir,
                stdio: ['ignore', 'pipe', 'pipe'],
                env: {
                    ...process.env,
                    PYTHONPATH: workingDir,
                    PYTHONUNBUFFERED: '1'
                }
            });

            let scriptOutput = '';
            let scriptError = '';

            // Timeout (longer in production)
            const timeout = isProduction ? 30000 : 20000;
            const timeoutId = setTimeout(() => {
                pythonProcess.kill('SIGKILL');
                reject(new Error('Timeout'));
            }, timeout);

            pythonProcess.stdout.on('data', (data) => {
                scriptOutput += data.toString();
            });

            pythonProcess.stderr.on('data', (data) => {
                scriptError += data.toString();
            });

            pythonProcess.on('close', (code) => {
                clearTimeout(timeoutId);
                
                if (code === 0 && scriptOutput) {
                    resolve(scriptOutput.trim());
                } else {
                    const errorMsg = scriptError || 'No output from Python script';
                    console.error(`❌ Python script failed (code ${code}):`, errorMsg);
                    reject(new Error(errorMsg));
                }
            });

            pythonProcess.on('error', (err) => {
                clearTimeout(timeoutId);
                console.error(`❌ Python process spawn error:`, err.message);
                reject(err);
            });
            
        } catch (error) {
            console.error(`❌ Failed to spawn fallback Python process:`, error.message);
            reject(new Error('Failed to start Python process'));
        }
    });
}

// 🔄 ENHANCED: Health check endpoint with more information
app.get('/health', (req, res) => {
    const health = {
        status: 'OK',
        pythonReady: isProcessReady,
        pendingRequests: pendingRequests.size,
        environment: isProduction ? 'production' : 'development',
        container: isContainer,
        timestamp: Date.now(),
        uptime: process.uptime(),
        memory: process.memoryUsage(),
        pythonPath: getPythonPath()
    };
    
    // Add Python process info if available
    if (pythonProcess) {
        health.pythonProcess = {
            pid: pythonProcess.pid,
            killed: pythonProcess.killed,
            exitCode: pythonProcess.exitCode
        };
    }
    
    res.json(health);
});

// 🔄 NEW: Additional health check for container orchestration
app.get('/ready', (req, res) => {
    if (isProcessReady) {
        res.status(200).json({ status: 'ready' });
    } else {
        res.status(503).json({ status: 'not ready', message: 'Python process not ready' });
    }
});

// Optimized chat endpoint
app.post("/chat", async (req, res) => {
    const startTime = Date.now();
    let requestId = `req_${++requestCounter}`;
    
    try {
        const { message, clientRequestId } = req.body;
        if (clientRequestId) requestId = clientRequestId;
        
        // Fast validation
        if (!message?.trim() || message.length > 1000) {
            return res.status(400).json({ 
                error: !message?.trim() ? "Message vide" : "Message trop long",
                requestId,
                timestamp: Date.now()
            });
        }

        console.log(`[${requestId}] Processing: "${message.substring(0, 50)}..."`);
        
        let response;
        let method = 'unknown';
        
        // Try persistent process first, fallback to spawn if not available
        try {
            if (isProcessReady) {
                response = await sendToPythonProcess(message.trim(), requestId);
                method = 'persistent';
                console.log(`[${requestId}] ✅ Persistent response in ${Date.now() - startTime}ms`);
            } else {
                throw new Error("Persistent process not ready");
            }
        } catch (persistentError) {
            console.log(`[${requestId}] 🔄 Falling back to spawn method: ${persistentError.message}`);
            try {
                response = await handleLLMFallback(message.trim(), requestId);
                method = 'fallback';
                console.log(`[${requestId}] ✅ Fallback response in ${Date.now() - startTime}ms`);
            } catch (fallbackError) {
                console.error(`[${requestId}] ❌ Both methods failed:`, fallbackError.message);
                throw fallbackError;
            }
        }
        
        res.json({ 
            response,
            requestId,
            method,
            processingTime: Date.now() - startTime,
            timestamp: Date.now()
        });
        
    } catch (error) {
        const processingTime = Date.now() - startTime;
        console.error(`[${requestId}] ❌ Error after ${processingTime}ms:`, error.message);
        
        let statusCode = 500;
        let errorMessage = "Erreur interne";
        
        if (error.message === 'Timeout') {
            statusCode = 504;
            errorMessage = "Délai d'attente dépassé";
        } else if (error.message.includes('not ready') || error.message.includes('Failed to start')) {
            statusCode = 503;
            errorMessage = "Service temporairement indisponible";
        }
        
        res.status(statusCode).json({ 
            error: errorMessage,
            requestId,
            processingTime,
            timestamp: Date.now()
        });
    }
});

// 404 handler
app.use((req, res) => {
    res.status(404).json({ error: 'Not found', timestamp: Date.now() });
});

// Start server and initialize Python process
app.listen(port, () => {
    console.log(` Server running on http://localhost:${port}`);
    console.log(` Started at: ${new Date().toISOString()}`);
    console.log(` Environment: ${isProduction ? 'Production' : 'Development'}`);
    console.log(` Python path: ${getPythonPath()}`);
    
    // Initialize persistent Python process for better performance
    setTimeout(initializePythonProcess, 1000); // Small delay to ensure server is ready
});

// Graceful shutdown
const gracefulShutdown = (signal) => {
    console.log(`\n Received ${signal}, shutting down gracefully...`);
    
    if (pythonProcess) {
        console.log(' Terminating Python process...');
        pythonProcess.kill('SIGTERM');
        
        // Force kill after 5 seconds
        setTimeout(() => {
            if (pythonProcess && !pythonProcess.killed) {
                console.log('🔪 Force killing Python process...');
                pythonProcess.kill('SIGKILL');
            }
        }, 5000);
    }
    
    // Clear pending requests
    for (const [requestId, { reject }] of pendingRequests) {
        reject(new Error('Server shutting down'));
    }
    pendingRequests.clear();
    
    setTimeout(() => {
        console.log(' Shutdown complete');
        process.exit(0);
    }, 2000);
};

process.on('SIGINT', () => gracefulShutdown('SIGINT'));
process.on('SIGTERM', () => gracefulShutdown('SIGTERM'));

// Handle uncaught exceptions
process.on('uncaughtException', (err) => {
    console.error(' Uncaught Exception:', err);
    gracefulShutdown('uncaughtException');
});

process.on('unhandledRejection', (reason, promise) => {
    console.error(' Unhandled Rejection at:', promise, 'reason:', reason);
    gracefulShutdown('unhandledRejection');
});