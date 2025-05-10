const express = require('express');
const multer = require('multer');
const path = require('path');
const fs = require('fs');
const cors = require('cors');
const app = express();
const PORT = 5000;
const IP  = '192.168.0.101';

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
app.listen(PORT, () => {
  console.log(`Server is running on http://${IP}:${PORT}`);
});
