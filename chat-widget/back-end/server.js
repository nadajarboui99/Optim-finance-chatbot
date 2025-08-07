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

// CORS configuration (simplified for development)
app.use(cors({
    origin: true, // Allow all origins in development
    methods: ['GET', 'POST', 'OPTIONS'],
    allowedHeaders: ['Content-Type', 'Accept', 'Authorization', 'x-request-id'],
    credentials: false
}));

app.use(express.json({ limit: '1mb' })); // Add size limit

// Optimized request logging (minimal overhead)
app.use((req, res, next) => {
    if (req.path === '/chat') {
        console.log(`[${Date.now()}] CHAT REQUEST`);
    }
    next();
});

/**
 * Initialize persistent Python process for faster responses
 */
function initializePythonProcess() {
    // Try persistent script first, fallback to original if not available
    const persistentScriptPath = path.join(__dirname, "../../Implementation/src/chatbot_persistent.py");
    const originalScriptPath = path.join(__dirname, "../../Implementation/src/chatbot.py");
    const pythonPath = '/Users/Apple/Documents/stages/Stage_StartNow/chatbot/.venv/bin/python';
    
    // Check if persistent script exists
    const fs = require('fs');
    const scriptPath = fs.existsSync(persistentScriptPath) ? persistentScriptPath : originalScriptPath;
    
    if (scriptPath === originalScriptPath) {
        console.log("⚠️ Using fallback mode - persistent script not found");
        return; // Don't start persistent process, use fallback for all requests
    }
    
    console.log("🔄 Starting persistent Python process...");
    
    pythonProcess = spawn(pythonPath, [scriptPath], {
        cwd: path.join(__dirname, "../../Implementation"),
        stdio: ['pipe', 'pipe', 'pipe'] // Enable stdin/stdout/stderr pipes
    });

    let buffer = '';
    
    pythonProcess.stdout.on('data', (data) => {
        buffer += data.toString();
        
        // Process complete responses (assuming newline-delimited JSON)
        const lines = buffer.split('\n');
        buffer = lines.pop(); // Keep incomplete line in buffer
        
        lines.forEach(line => {
            if (line.trim()) {
                try {
                    const response = JSON.parse(line);
                    handlePythonResponse(response);
                } catch (e) {
                    console.error("Failed to parse Python response:", line);
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
        // Auto-restart on unexpected closure
        setTimeout(initializePythonProcess, 1000);
    });

    pythonProcess.on('error', (err) => {
        console.error("❌ Python process error:", err.message);
        isProcessReady = false;
    });
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
        
        // Set timeout
        setTimeout(() => {
            if (pendingRequests.has(requestId)) {
                pendingRequests.delete(requestId);
                reject(new Error("Request timeout"));
            }
        }, 15000); // Reduced timeout to 15s

        // Send request to Python process
        const request = JSON.stringify({
            requestId,
            message,
            timestamp: Date.now()
        }) + '\n';
        
        pythonProcess.stdin.write(request);
    });
}

/**
 * Fallback function using your original chatbot.py script
 */
function handleLLMFallback(message, clientRequestId) {
    return new Promise((resolve, reject) => {
        const pythonScriptPath = path.join(__dirname, "../../Implementation/src/chatbot.py");
        const pythonPath = '/Users/Apple/Documents/stages/Stage_StartNow/chatbot/.venv/bin/python';
        
        const pythonProcess = spawn(pythonPath, [pythonScriptPath, message], {
            cwd: path.join(__dirname, "../../Implementation"),
            stdio: ['ignore', 'pipe', 'pipe'] // Optimized stdio
        });

        let scriptOutput = '';
        let scriptError = '';

        // Reduced timeout
        const timeoutId = setTimeout(() => {
            pythonProcess.kill('SIGKILL'); // Force kill
            reject(new Error('Timeout'));
        }, 20000); // 20s timeout

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
                reject(new Error(scriptError || 'No output from Python script'));
            }
        });

        pythonProcess.on('error', (err) => {
            clearTimeout(timeoutId);
            reject(err);
        });
    });
}

// Health check endpoint
app.get('/health', (req, res) => {
    res.json({ 
        status: 'OK',
        pythonReady: isProcessReady,
        pendingRequests: pendingRequests.size,
        timestamp: Date.now()
    });
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
        
        // Try persistent process first, fallback to spawn if not available
        try {
            if (isProcessReady) {
                response = await sendToPythonProcess(message.trim(), requestId);
                console.log(`[${requestId}] ✅ Persistent response in ${Date.now() - startTime}ms`);
            } else {
                throw new Error("Persistent process not ready");
            }
        } catch (persistentError) {
            console.log(`[${requestId}] 🔄 Falling back to spawn method`);
            response = await handleLLMFallback(message.trim(), requestId);
            console.log(`[${requestId}] ✅ Fallback response in ${Date.now() - startTime}ms`);
        }
        
        res.json({ 
            response,
            requestId,
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
        } else if (error.message.includes('not ready')) {
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

// 404 handler (minimal)
app.use((req, res) => {
    res.status(404).json({ error: 'Not found', timestamp: Date.now() });
});

// Start server and initialize Python process
app.listen(port, () => {
    console.log(`🚀 Server running on http://localhost:${port}`);
    console.log(`🕐 Started at: ${new Date().toISOString()}`);
    
    // Initialize persistent Python process for better performance
    initializePythonProcess();
});

// Graceful shutdown
const gracefulShutdown = () => {
    console.log('\n🛑 Shutting down gracefully...');
    
    if (pythonProcess) {
        pythonProcess.kill();
    }
    
    setTimeout(() => process.exit(0), 1000);
};

process.on('SIGINT', gracefulShutdown);
process.on('SIGTERM', gracefulShutdown);

// Handle uncaught exceptions
process.on('uncaughtException', (err) => {
    console.error('Uncaught Exception:', err);
    gracefulShutdown();
});

process.on('unhandledRejection', (reason) => {
    console.error('Unhandled Rejection:', reason);
    gracefulShutdown();
});