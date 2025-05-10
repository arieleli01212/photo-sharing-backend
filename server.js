const express = require('express');
const multer = require('multer');
const path = require('path');
const fs = require('fs');
const cors = require('cors');
const app = express();
const http    = require("http");
const { Server } = require("socket.io");


const IP  = '172.20.10.6';
const PORT = 5000;


// Setup multer for image upload
const upload = multer({
  dest: 'uploads/', // Folder where uploaded images will be stored
  fileFilter: (req, file, cb) => {
    const ext = path.extname(file.originalname);
    if (ext !== '.jpg' && ext !== '.jpeg' && ext !== '.png') {
      return cb(new Error('Only image files are allowed!'), false);
    }
    cb(null, true);
  }
});

// Allow CORS for local development
app.use(cors());

const server = http.createServer(app);
const io     = new Server(server, { cors: { origin: "*" },path: "/socket.io" });
let guestCount = 0;

/* REST endpoint so the page can get the value on first paint */
app.get("/guest", (req, res) => res.json({ count: guestCount }));

io.on("connection", (socket) => {
  guestCount++;
  io.emit("guestCount", guestCount);         // broadcast to all
  console.log("➕ connected", guestCount);

  socket.on("disconnect", () => {
    guestCount = Math.max(guestCount - 1, 0);
    io.emit("guestCount", guestCount);
    console.log("➖ disconnected", guestCount);
  });
});

// Serve images from the uploads folder
app.use('/uploads', express.static('uploads'));

// Route to get list of images
app.get('/get-images', (req, res) => {
  const imageDir = path.join(__dirname, 'uploads');
  console.log('GET /get-images: Reading images from uploads directory...');
  
  fs.readdir(imageDir, (err, files) => {
    if (err) {
      console.error('Error reading uploads directory:', err);
      return res.status(500).json({ error: 'Unable to read uploads directory' });
    }
    // Filter the files to get only image files
    const imageFiles = files;

    console.log(`GET /get-images: Found ${imageFiles.length} images`);

    // Map the file names to their URLs
    const imageUrls = imageFiles.map(file => `http://${IP}:${PORT}/uploads/${file}`);
    res.json(imageUrls);
  });
});

// Handle image upload
app.post('/upload', upload.array('images', 10), (req, res) => {
  console.log('POST /upload: Uploading images...');
  console.log('Uploaded files:', req.files);

  const filePaths = req.files.map(file => `http://${IP}:${PORT}/uploads/${file.filename}`);
  
  console.log('POST /upload: Returning file paths:', filePaths);
  res.json({ filePaths });
});

// Start server
server.listen(PORT,"0.0.0.0", () => {
  console.log(`Server is running on http://${IP}:${PORT}`);
});
