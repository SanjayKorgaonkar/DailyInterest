const { app, BrowserWindow, dialog } = require("electron");
const path = require("path");
const http = require("http");
const fs = require("fs");
const { spawn } = require("child_process");

let mongoProcess = null;
let backendProcess = null;
let staticServer = null;
let mainWindow = null;

const resourcesPath = app.isPackaged
  ? process.resourcesPath
  : path.join(__dirname, "resources");

const mongoDataDir = path.join(app.getPath("userData"), "mongo-data");
const MONGO_PORT = 27018;
const BACKEND_PORT = 8001;
const FRONTEND_PORT = 3000;

function ensureDir(p) {
  if (!fs.existsSync(p)) fs.mkdirSync(p, { recursive: true });
}

function startMongo() {
  return new Promise((resolve, reject) => {
    ensureDir(mongoDataDir);
    const mongodPath = path.join(resourcesPath, "mongodb", "mongod.exe");
    if (!fs.existsSync(mongodPath)) {
      reject(new Error(`mongod.exe not found at ${mongodPath}.\nSee BUILD_WINDOWS.md for how to add it.`));
      return;
    }
    mongoProcess = spawn(mongodPath, ["--dbpath", mongoDataDir, "--port", String(MONGO_PORT), "--bind_ip", "127.0.0.1"]);
    mongoProcess.on("error", reject);
    // mongod binds its port quickly on a local data dir; a short fixed wait is reliable
    setTimeout(resolve, 2500);
  });
}

function startBackend() {
  return new Promise((resolve, reject) => {
    const backendPath = path.join(resourcesPath, "backend", "ledgerline-backend.exe");
    if (!fs.existsSync(backendPath)) {
      reject(new Error(`Backend executable not found at ${backendPath}.\nSee BUILD_WINDOWS.md.`));
      return;
    }
    backendProcess = spawn(backendPath, [], {
      env: {
        ...process.env,
        MONGO_URL: `mongodb://127.0.0.1:${MONGO_PORT}`,
        DB_NAME: "ledgerline",
        CORS_ORIGINS: "*",
        PORT: String(BACKEND_PORT),
      },
    });
    backendProcess.on("error", reject);
    waitForBackend(resolve, reject, 40);
  });
}

function waitForBackend(resolve, reject, attemptsLeft) {
  if (attemptsLeft <= 0) {
    reject(new Error("Backend did not respond in time."));
    return;
  }
  http
    .get(`http://127.0.0.1:${BACKEND_PORT}/api/`, (res) => {
      if (res.statusCode === 200) resolve();
      else setTimeout(() => waitForBackend(resolve, reject, attemptsLeft - 1), 500);
    })
    .on("error", () => setTimeout(() => waitForBackend(resolve, reject, attemptsLeft - 1), 500));
}

function startStaticServer() {
  return new Promise((resolve) => {
    const buildDir = path.join(resourcesPath, "frontend-build");
    const mime = {
      ".html": "text/html", ".js": "application/javascript", ".css": "text/css",
      ".png": "image/png", ".jpg": "image/jpeg", ".svg": "image/svg+xml",
      ".json": "application/json", ".ico": "image/x-icon", ".woff": "font/woff", ".woff2": "font/woff2",
    };
    staticServer = http.createServer((req, res) => {
      let filePath = path.join(buildDir, decodeURIComponent(req.url.split("?")[0]));
      if (!fs.existsSync(filePath) || fs.statSync(filePath).isDirectory()) {
        filePath = path.join(buildDir, "index.html");
      }
      fs.readFile(filePath, (err, data) => {
        if (err) {
          res.writeHead(404);
          res.end("Not found");
          return;
        }
        res.writeHead(200, { "Content-Type": mime[path.extname(filePath)] || "application/octet-stream" });
        res.end(data);
      });
    });
    staticServer.listen(FRONTEND_PORT, "127.0.0.1", resolve);
  });
}

async function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1440,
    height: 900,
    title: "Ledgerline",
    icon: path.join(resourcesPath, "icon.png"),
    webPreferences: { contextIsolation: true, nodeIntegration: false },
  });
  mainWindow.setMenuBarVisibility(false);
  await mainWindow.loadURL(`http://127.0.0.1:${FRONTEND_PORT}`);
}

function killAll() {
  if (backendProcess) backendProcess.kill();
  if (mongoProcess) mongoProcess.kill();
  if (staticServer) staticServer.close();
}

app.whenReady().then(async () => {
  try {
    await startMongo();
    await startBackend();
    await startStaticServer();
    await createWindow();
  } catch (err) {
    dialog.showErrorBox("Ledgerline failed to start", String(err.message || err));
    app.quit();
  }
});

app.on("window-all-closed", () => {
  killAll();
  app.quit();
});
app.on("before-quit", killAll);
