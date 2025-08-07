const express = require("express");
const cors = require("cors");
const { spawn } = require("child_process");
const path = require("path");

const app = express();
const port = 3000;

// CORS configuration
const corsOptions = {
    origin: function (origin, callback) {
        const allowedOrigins = [
            'http://localhost:3000',
            'http://localhost:5500',
            'http://127.0.0.1:3000',
            'http://127.0.0.1:5500',
            null // Allows file:// protocol
        ];
        if (allowedOrigins.includes(origin) || !origin) {
            return callback(null, true);
        }
        return callback(null, true); // Allow all origins in development
    },
    methods: ['GET', 'POST', 'OPTIONS'],
    allowedHeaders: ['Content-Type', 'Accept', 'Authorization', 'x-request-id'],
    credentials: false
};

app.use(cors(corsOptions));

// Handle preflight requests
app.use((req, res, next) => {
    if (req.method === 'OPTIONS') {
        res.header('Access-Control-Allow-Origin', req.headers.origin || '*');
        res.header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS');
        res.header('Access-Control-Allow-Headers', 'Content-Type, Accept, Authorization, x-request-id');
        return res.sendStatus(200);
    }
    next();
});

app.use(express.json());

// Request logging
app.use((req, res, next) => {
    console.log(`${new Date().toISOString()} - ${req.method} ${req.path}`);
    console.log('Origin:', req.headers.origin || 'undefined');
    next();
});

/**
 * Function to call the Python script and get chatbot response
 */
function handleLLM(message, clientRequestId) {
    return new Promise((resolve, reject) => {
        const pythonScriptPath = path.join(__dirname, "../../Implementation/src/chatbot.py");
        const pythonPath = '/Users/Apple/Documents/stages/Stage_StartNow/chatbot/.venv/bin/python'; // Updated path
        
        console.log(`🐍 Calling Python script: ${pythonScriptPath}`);
        console.log(`💬 With message: "${message}"`);
        
        const pythonProcess = spawn(pythonPath, [pythonScriptPath, message], {
            cwd: path.join(__dirname, "../../Implementation") // Working directory for imports
        });

        let scriptOutput = '';
        let scriptError = '';

        const timeoutId = setTimeout(() => {
            pythonProcess.kill();
            console.error(`${new Date().toISOString()} - Python script timeout after 25s`);
            reject({
                type: 'timeout',
                message: 'Python script timeout after 25s'
            });
        }, 50000); // 25s timeout to stay within frontend's 30s limit

        pythonProcess.stdout.on('data', (data) => {
            scriptOutput += data.toString();
        });

        pythonProcess.stderr.on('data', (data) => {
            scriptError += data.toString();
        });

        pythonProcess.on('close', (code) => {
            clearTimeout(timeoutId);
            console.log(`${new Date().toISOString()} - Python script completed with code ${code}`);
            
            if (code === 0 && scriptOutput) {
                console.log(`✅ Python script output: ${scriptOutput.substring(0, 100)}${scriptOutput.length > 100 ? '...' : ''}`);
                resolve(scriptOutput.trim());
            } else {
                console.error(`❌ Python script error: ${scriptError || 'No output'}`);
                reject({
                    type: 'python_error',
                    message: scriptError || 'No output from Python script',
                    code
                });
            }
        });

        pythonProcess.on('error', (err) => {
            clearTimeout(timeoutId);
            console.error(`❌ Python process error: ${err.message}`);
            reject({
                type: 'python_error',
                message: err.message
            });
        });
    });
}

// Health check endpoint
app.get('/health', (req, res) => {
    res.json({ 
        status: 'OK', 
        timestamp: new Date().toISOString(),
        service: 'OPTIM Finance Chatbot Backend'
    });
});

// Test endpoint
app.post("/test", (req, res) => {
    console.log("Test endpoint hit");
    const { message } = req.body;
    
    if (!message) {
        return res.status(400).json({ error: "Message required" });
    }
    
    res.json({ 
        response: `Test echo: ${message}`,
        timestamp: new Date().toISOString(),
        status: 'success'
    });
});

// Main chat endpoint
app.post("/chat", async (req, res) => {
    let clientRequestId = null; // Default value
    try {
        const { message, clientRequestId: requestId } = req.body;
        clientRequestId = requestId; // Assign value
        
        // Validate input
        if (!message) {
            return res.status(400).json({ 
                error: "Message manquant",
                code: "MISSING_MESSAGE",
                requestId: clientRequestId,
                timestamp: new Date().toISOString()
            });
        }
        
        if (typeof message !== 'string') {
            return res.status(400).json({ 
                error: "Le message doit être une chaîne de caractères",
                code: "INVALID_MESSAGE_TYPE",
                requestId: clientRequestId,
                timestamp: new Date().toISOString()
            });
        }
        
        if (message.trim().length === 0) {
            return res.status(400).json({ 
                error: "Le message ne peut pas être vide",
                code: "EMPTY_MESSAGE",
                requestId: clientRequestId,
                timestamp: new Date().toISOString()
            });
        }
        
        if (message.length > 1000) {
            return res.status(400).json({ 
                error: "Le message est trop long (maximum 1000 caractères)",
                code: "MESSAGE_TOO_LONG",
                requestId: clientRequestId,
                timestamp: new Date().toISOString()
            });
        }
        
        console.log(`Processing user message: "${message.substring(0, 100)}${message.length > 100 ? '...' : ''}"`);
        
        const response = await handleLLM(message.trim(), clientRequestId);
        
        console.log(`Chatbot response: "${response.substring(0, 100)}${response.length > 100 ? '...' : ''}"`);
        
        res.json({ 
            response: response,
            requestId: clientRequestId,
            timestamp: new Date().toISOString(),
            status: 'success'
        });
        
    } catch (error) {
        console.error("Server error:", error);
        
        let errorMessage = "Erreur interne du serveur";
        let errorCode = "INTERNAL_ERROR";
        let statusCode = 500;
        
        if (error.type === 'timeout') {
            errorMessage = "Le script Python a pris trop de temps";
            errorCode = "PYTHON_TIMEOUT";
            statusCode = 504;
        } else if (error.type === 'python_error') {
            errorMessage = `Erreur lors de l'exécution du chatbot: ${error.message}`;
            errorCode = "CHATBOT_ERROR";
            if (error.message.includes('No such file')) {
                errorMessage = "Script Python introuvable. Vérifiez le chemin.";
                errorCode = "PYTHON_SCRIPT_NOT_FOUND";
            }
        }
        
        res.status(statusCode).json({ 
            error: errorMessage,
            code: errorCode,
            requestId: clientRequestId || 'unknown',
            timestamp: new Date().toISOString(),
            details: error.message // Include detailed error message
        });
    }
});

// Handle GET /chat (unsupported)
app.get("/chat", (req, res) => {
    console.log(`${new Date().toISOString()} - GET /chat (unsupported)`);
    res.status(405).json({ 
        error: "Méthode non autorisée. Utilisez POST pour les requêtes de chat.",
        code: "METHOD_NOT_ALLOWED",
        timestamp: new Date().toISOString()
    });
});

// 404 handler
app.use((req, res) => {
    res.status(404).json({ 
        error: 'Endpoint non trouvé',
        code: 'NOT_FOUND',
        path: req.path,
        timestamp: new Date().toISOString()
    });
});

// Error handling middleware
app.use((err, req, res, next) => {
    console.error('Unhandled error:', err);
    res.status(500).json({ 
        error: 'Erreur interne du serveur',
        code: 'UNHANDLED_ERROR',
        timestamp: new Date().toISOString()
    });
});

// Start server
app.listen(port, () => {
    console.log(`🚀 Serveur Node.js lancé sur http://localhost:${port}`);
    console.log(`📊 Health check: http://localhost:${port}/health`);
    console.log(`🧪 Test endpoint: http://localhost:${port}/test`);
    console.log(`💬 Chat endpoint: http://localhost:${port}/chat`);
    console.log(`🕐 Started at: ${new Date().toISOString()}`);
    console.log(`📂 Working directory: ${__dirname}`);
});

// Graceful shutdown
process.on('SIGINT', () => {
    console.log('\n🛑 Arrêt du serveur...');
    process.exit(0);
});

process.on('SIGTERM', () => {
    console.log('\n🛑 Arrêt du serveur...');
    process.exit(0);
});

// Handle uncaught exceptions
process.on('uncaughtException', (err) => {
    console.error('Uncaught Exception:', err);
    process.exit(1);
});

process.on('unhandledRejection', (reason, promise) => {
    console.error('Unhandled Rejection at:', promise, 'reason:', reason);
    process.exit(1);
});