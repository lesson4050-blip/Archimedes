const fs = require('fs');
const path = require('path');
const sharp = require('sharp');

// ── Pure-JS Packagers ───────────────────────────────────

/**
 * Packs PNG buffers into a multi-resolution Windows ICO file.
 * @param {Buffer[]} pngBuffers - Array of PNG buffers
 * @param {number[]} sizes - Corresponding square sizes
 * @returns {Buffer} - ICO file buffer
 */
function packIco(pngBuffers, sizes) {
  const header = Buffer.alloc(6);
  header.writeUInt16LE(0, 0); // Reserved
  header.writeUInt16LE(1, 2); // Type (1 = ICO)
  header.writeUInt16LE(pngBuffers.length, 4); // Number of images

  const entries = [];
  let offset = 6 + pngBuffers.length * 16;

  for (let i = 0; i < pngBuffers.length; i++) {
    const buf = pngBuffers[i];
    const size = sizes[i];
    const entry = Buffer.alloc(16);
    entry.writeUInt8(size >= 256 ? 0 : size, 0); // Width
    entry.writeUInt8(size >= 256 ? 0 : size, 1); // Height
    entry.writeUInt8(0, 2); // Color palette
    entry.writeUInt8(0, 3); // Reserved
    entry.writeUInt16LE(1, 4); // Planes
    entry.writeUInt16LE(32, 6); // Bits per pixel
    entry.writeUInt32LE(buf.length, 8); // Image size
    entry.writeUInt32LE(offset, 12); // Image offset
    entries.push(entry);
    offset += buf.length;
  }

  return Buffer.concat([header, ...entries, ...pngBuffers]);
}

/**
 * Packs PNG buffers into a macOS Apple ICNS file.
 * @param {Object} pngBuffersMap - Object mapping ICNS keys (e.g. 'ic07') to PNG buffers
 * @returns {Buffer} - ICNS file buffer
 */
function packIcns(pngBuffersMap) {
  const entries = [];
  let totalLength = 8; // ICNS Header size

  for (const [key, buf] of Object.entries(pngBuffersMap)) {
    const keyBuf = Buffer.from(key, 'ascii');
    const sizeBuf = Buffer.alloc(4);
    const entrySize = 8 + buf.length;
    sizeBuf.writeUInt32BE(entrySize, 0);
    entries.push(keyBuf, sizeBuf, buf);
    totalLength += entrySize;
  }

  const header = Buffer.alloc(8);
  header.write('icns', 0, 4, 'ascii');
  header.writeUInt32BE(totalLength, 4);

  return Buffer.concat([header, ...entries]);
}

// ── Main Generation Routine ────────────────────────────

async function main() {
  const logoIconPath = path.join(__dirname, '../assets/logos/logo-icon.svg');
  const logoIconWhitePath = path.join(__dirname, '../assets/logos/logo-icon-white.svg');
  const logoFullPath = path.join(__dirname, '../assets/logos/logo-full.svg');
  const logoFullWhitePath = path.join(__dirname, '../assets/logos/logo-full-white.svg');

  // Colors from Design System (docs/DESIGN_SYSTEM.md)
  const bgBaseColor = '#0f172a'; // slate-900
  const primaryColor = '#6366f1'; // indigo-500

  console.log('Starting icon generation...');

  // Helper to ensure target directories exist
  const ensureDir = (filePath) => {
    const dir = path.dirname(filePath);
    if (!fs.existsSync(dir)) {
      fs.mkdirSync(dir, { recursive: true });
    }
  };

  // Helper to render simple PNG icon (transparent bg)
  const renderIcon = async (size, outputPath, white = false) => {
    ensureDir(outputPath);
    const src = white ? logoIconWhitePath : logoIconPath;
    await sharp(src)
      .resize(size, size)
      .png({ quality: 85 })
      .toFile(outputPath);
    console.log(`Generated: ${outputPath} (${size}x${size})`);
  };

  // Helper to render PNG icon with solid background color
  const renderIconSolid = async (size, outputPath, bgColor) => {
    ensureDir(outputPath);
    const logoBuffer = await sharp(logoIconWhitePath)
      .resize(size, size)
      .toBuffer();
    await sharp({
      create: {
        width: size,
        height: size,
        channels: 4,
        background: bgColor,
      }
    })
      .composite([{ input: logoBuffer, blend: 'over' }])
      .png({ quality: 85 })
      .toFile(outputPath);
    console.log(`Generated Solid Icon: ${outputPath} (${size}x${size})`);
  };

  // ── 1. Web Platform (Next.js) ───────────────────────────
  console.log('\n--- Generating Web Icons ---');
  
  // favicon PNGs
  await renderIcon(16, path.join(__dirname, '../public/favicon-16x16.png'));
  await renderIcon(32, path.join(__dirname, '../public/favicon-32x32.png'));
  
  // favicon ICO
  const fav16 = await sharp(logoIconPath).resize(16, 16).png({ quality: 85 }).toBuffer();
  const fav32 = await sharp(logoIconPath).resize(32, 32).png({ quality: 85 }).toBuffer();
  const faviconIco = packIco([fav16, fav32], [16, 32]);
  const faviconIcoPath = path.join(__dirname, '../public/favicon.ico');
  ensureDir(faviconIcoPath);
  fs.writeFileSync(faviconIcoPath, faviconIco);
  console.log(`Generated multi-resolution ICO: ${faviconIcoPath}`);

  // Next.js standard icons
  await renderIcon(180, path.join(__dirname, '../public/apple-touch-icon.png'));
  await renderIcon(192, path.join(__dirname, '../public/android-chrome-192x192.png'));
  await renderIcon(512, path.join(__dirname, '../public/android-chrome-512x512.png'));
  await renderIcon(150, path.join(__dirname, '../public/mstile-150x150.png'));

  // OG-Image (1200x630, logo-full centered on slate-900 background)
  const ogPath = path.join(__dirname, '../public/og-image.png');
  ensureDir(ogPath);
  // We want the logo to be centered. Let's make it 600px wide, natural height.
  // We will read logo-full-white.svg and resize to width 600.
  const ogLogoBuffer = await sharp(logoFullWhitePath)
    .resize({ width: 600 })
    .toBuffer();
  await sharp({
    create: {
      width: 1200,
      height: 630,
      channels: 4,
      background: bgBaseColor,
    }
  })
    .composite([{ input: ogLogoBuffer, blend: 'over' }])
    .png({ quality: 85 })
    .toFile(ogPath);
  console.log(`Generated OG Image: ${ogPath} (1200x630)`);

  // ── 2. Desktop Platform (Tauri v2) ─────────────────────
  console.log('\n--- Generating Desktop Icons ---');
  
  // Tauri PNGs
  await renderIcon(32, path.join(__dirname, '../src-tauri/icons/32x32.png'));
  await renderIcon(64, path.join(__dirname, '../src-tauri/icons/64x64.png'));
  await renderIcon(128, path.join(__dirname, '../src-tauri/icons/128x128.png'));
  await renderIcon(256, path.join(__dirname, '../src-tauri/icons/128x128@2x.png')); // 256x256 named @2x

  // Windows icon.ico (16, 24, 32, 48, 64, 256)
  const icoSizes = [16, 24, 32, 48, 64, 256];
  const icoBuffers = [];
  for (const s of icoSizes) {
    const buf = await sharp(logoIconPath).resize(s, s).png({ quality: 85 }).toBuffer();
    icoBuffers.push(buf);
  }
  const iconIco = packIco(icoBuffers, icoSizes);
  const iconIcoPath = path.join(__dirname, '../src-tauri/icons/icon.ico');
  ensureDir(iconIcoPath);
  fs.writeFileSync(iconIcoPath, iconIco);
  console.log(`Generated Windows App ICO: ${iconIcoPath}`);

  // macOS icon.icns (multiple sizes)
  const icnsMap = {
    icp4: await sharp(logoIconPath).resize(16, 16).png({ quality: 85 }).toBuffer(),
    icp5: await sharp(logoIconPath).resize(32, 32).png({ quality: 85 }).toBuffer(),
    icp6: await sharp(logoIconPath).resize(64, 64).png({ quality: 85 }).toBuffer(),
    ic07: await sharp(logoIconPath).resize(128, 128).png({ quality: 85 }).toBuffer(),
    ic08: await sharp(logoIconPath).resize(256, 256).png({ quality: 85 }).toBuffer(),
    ic09: await sharp(logoIconPath).resize(512, 512).png({ quality: 85 }).toBuffer(),
    ic10: await sharp(logoIconPath).resize(1024, 1024).png({ quality: 85 }).toBuffer(),
    ic11: await sharp(logoIconPath).resize(32, 32).png({ quality: 85 }).toBuffer(), // 16x16@2x
    ic12: await sharp(logoIconPath).resize(64, 64).png({ quality: 85 }).toBuffer(), // 32x32@2x
    ic13: await sharp(logoIconPath).resize(256, 256).png({ quality: 85 }).toBuffer(), // 128x128@2x
    ic14: await sharp(logoIconPath).resize(512, 512).png({ quality: 85 }).toBuffer(), // 256x256@2x
  };
  const iconIcns = packIcns(icnsMap);
  const iconIcnsPath = path.join(__dirname, '../src-tauri/icons/icon.icns');
  ensureDir(iconIcnsPath);
  fs.writeFileSync(iconIcnsPath, iconIcns);
  console.log(`Generated macOS App ICNS: ${iconIcnsPath}`);

  // ── 3. Mobile Platform (Capacitor) ──────────────────────
  console.log('\n--- Generating Mobile Icons ---');
  
  // Android launcher mipmaps
  // mdpi: 48, hdpi: 72, xhdpi: 96, xxhdpi: 144, xxxhdpi: 192
  await renderIcon(48, path.join(__dirname, '../android/app/src/main/res/mipmap-mdpi/ic_launcher.png'));
  await renderIcon(72, path.join(__dirname, '../android/app/src/main/res/mipmap-hdpi/ic_launcher.png'));
  await renderIcon(96, path.join(__dirname, '../android/app/src/main/res/mipmap-xhdpi/ic_launcher.png'));
  await renderIcon(144, path.join(__dirname, '../android/app/src/main/res/mipmap-xxhdpi/ic_launcher.png'));
  await renderIcon(192, path.join(__dirname, '../android/app/src/main/res/mipmap-xxxhdpi/ic_launcher.png'));
  
  // Android launcher round (uses indigo background)
  await renderIconSolid(192, path.join(__dirname, '../android/app/src/main/res/mipmap-xxxhdpi/ic_launcher_round.png'), primaryColor);

  // iOS AppIcon.appiconset
  const iosSizes = [
    { size: 20, scale: 2, name: 'icon-20x20@2x.png' },
    { size: 20, scale: 3, name: 'icon-20x20@3x.png' },
    { size: 29, scale: 1, name: 'icon-29x29@1x.png' },
    { size: 29, scale: 2, name: 'icon-29x29@2x.png' },
    { size: 29, scale: 3, name: 'icon-29x29@3x.png' },
    { size: 40, scale: 1, name: 'icon-40x40@1x.png' },
    { size: 40, scale: 2, name: 'icon-40x40@2x.png' },
    { size: 40, scale: 3, name: 'icon-40x40@3x.png' },
    { size: 60, scale: 2, name: 'icon-60x60@2x.png' },
    { size: 60, scale: 3, name: 'icon-60x60@3x.png' },
    { size: 76, scale: 1, name: 'icon-76x76@1x.png' },
    { size: 76, scale: 2, name: 'icon-76x76@2x.png' },
    { size: 83.5, scale: 2, name: 'icon-83.5x83.5@2x.png' },
    { size: 1024, scale: 1, name: 'icon-1024x1024@1x.png' }
  ];

  const iosDir = path.join(__dirname, '../ios/App/App/Assets.xcassets/AppIcon.appiconset/');
  for (const { size, scale, name } of iosSizes) {
    const actualSize = Math.floor(size * scale);
    const outputPath = path.join(iosDir, name);
    // iOS icons MUST be solid (App Store guidelines). Use slate-900 as base.
    await renderIconSolid(actualSize, outputPath, bgBaseColor);
  }

  // Generate Contents.json for iOS AppIcon
  const contentsJson = {
    images: [
      { size: '20x20', idiom: 'iphone', scale: '2x', filename: 'icon-20x20@2x.png' },
      { size: '20x20', idiom: 'iphone', scale: '3x', filename: 'icon-20x20@3x.png' },
      { size: '29x29', idiom: 'iphone', scale: '1x', filename: 'icon-29x29@1x.png' },
      { size: '29x29', idiom: 'iphone', scale: '2x', filename: 'icon-29x29@2x.png' },
      { size: '29x29', idiom: 'iphone', scale: '3x', filename: 'icon-29x29@3x.png' },
      { size: '40x40', idiom: 'iphone', scale: '2x', filename: 'icon-40x40@2x.png' },
      { size: '40x40', idiom: 'iphone', scale: '3x', filename: 'icon-40x40@3x.png' },
      { size: '60x60', idiom: 'iphone', scale: '2x', filename: 'icon-60x60@2x.png' },
      { size: '60x60', idiom: 'iphone', scale: '3x', filename: 'icon-60x60@3x.png' },
      { size: '20x20', idiom: 'ipad', scale: '1x', filename: 'icon-20x20@1x.png' },
      { size: '20x20', idiom: 'ipad', scale: '2x', filename: 'icon-20x20@2x.png' },
      { size: '29x29', idiom: 'ipad', scale: '1x', filename: 'icon-29x29@1x.png' },
      { size: '29x29', idiom: 'ipad', scale: '2x', filename: 'icon-29x29@2x.png' },
      { size: '40x40', idiom: 'ipad', scale: '1x', filename: 'icon-40x40@1x.png' },
      { size: '40x40', idiom: 'ipad', scale: '2x', filename: 'icon-40x40@2x.png' },
      { size: '76x76', idiom: 'ipad', scale: '1x', filename: 'icon-76x76@1x.png' },
      { size: '76x76', idiom: 'ipad', scale: '2x', filename: 'icon-76x76@2x.png' },
      { size: '83.5x83.5', idiom: 'ipad', scale: '2x', filename: 'icon-83.5x83.5@2x.png' },
      { size: '1024x1024', idiom: 'ios-marketing', scale: '1x', filename: 'icon-1024x1024@1x.png' }
    ],
    info: {
      version: 1,
      author: 'xcode'
    }
  };
  fs.writeFileSync(path.join(iosDir, 'Contents.json'), JSON.stringify(contentsJson, null, 2));
  console.log(`Generated: ${path.join(iosDir, 'Contents.json')}`);

  console.log('\nAll icons successfully generated!');
}

main().catch(err => {
  console.error('Error generating icons:', err);
  process.exit(1);
});
