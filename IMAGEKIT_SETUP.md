# ImageKit.io Integration Setup Guide

This guide will help you set up ImageKit.io for faster image delivery in your sports management application. ImageKit.io provides real-time image optimization, transformations, and faster CDN delivery compared to GitHub storage.

## 🚀 Benefits of ImageKit.io over GitHub

- **Faster Loading**: Global CDN with edge caching
- **Automatic Optimization**: WebP/AVIF conversion, compression
- **Real-time Transformations**: Resize, crop, format conversion on-the-fly
- **Better Performance**: Optimized for image delivery
- **Smart Features**: Lazy loading, responsive images, AI-powered optimizations

## 📋 Prerequisites

1. **ImageKit.io Account**: Sign up at [imagekit.io](https://imagekit.io)
2. **Python Dependencies**: Already installed via `pip install imagekitio`

## 🔧 Setup Steps

### Step 1: Create ImageKit.io Account and Get Credentials

1. Go to [imagekit.io](https://imagekit.io) and create a free account
2. Once logged in, go to your **Dashboard** → **Developer** → **API Keys**
3. Copy the following credentials:
   - **Public Key**
   - **Private Key**
   - **URL Endpoint** (looks like `https://ik.imagekit.io/your_imagekit_id`)

### Step 2: Configure Environment Variables

Add these environment variables to your system or `.env` file:

```bash
# ImageKit.io Configuration
IMAGEKIT_PRIVATE_KEY=private_your_private_key_here
IMAGEKIT_PUBLIC_KEY=public_your_public_key_here
IMAGEKIT_URL_ENDPOINT=https://ik.imagekit.io/your_imagekit_id

# Optional: Set preferred storage method (imagekit, github, or local)
PREFERRED_LOGO_STORAGE=imagekit
```

### Step 3: Run Database Migration

Run the database migration to add ImageKit support to existing databases:

```bash
python migrations/add_imagekit_support.py
```

This will:
- Add the `imagekit_file_id` column to the Team table
- Update documentation for storage types
- Show current storage distribution

### Step 4: Test the Setup

1. **Start your application** as usual
2. **Upload a new team logo** through:
   - Registration form
   - Team profile editing
   - Admin team management
3. **Verify ImageKit is working** by checking:
   - The image loads faster
   - The URL contains your ImageKit endpoint
   - Image transformations are applied automatically

### Step 5: Migrate Existing Images (Optional)

If you have existing team logos stored in GitHub, you can migrate them to ImageKit:

```bash
# Preview what would be migrated (safe)
python migrate_to_imagekit.py --dry-run

# Perform the actual migration
python migrate_to_imagekit.py

# Migrate only a specific team
python migrate_to_imagekit.py --team-id 123

# Force migration even if already on ImageKit
python migrate_to_imagekit.py --force
```

## 🎯 Image Optimization Features

The integration automatically provides different optimized versions based on context:

### Transformation Contexts

- **thumbnail**: 50×50px, high quality (navigation, small previews)
- **card**: 100×100px, balanced quality (team cards, lists)
- **hero**: 200×200px, high quality (profile pages, headers)
- **avatar**: 40×40px, rounded, optimized (user avatars)

### Automatic Optimizations

- **Format Conversion**: Automatically serves WebP/AVIF when supported
- **Compression**: Optimized file sizes without quality loss
- **Responsive**: Serves appropriate sizes based on device
- **Lazy Loading**: Images load as they enter the viewport

## 🔄 How It Works

1. **Upload Priority**: 
   - ImageKit.io (if configured)
   - GitHub (if configured)
   - Local storage (fallback)

2. **URL Generation**:
   - ImageKit images use optimized CDN URLs with transformations
   - GitHub images use direct GitHub URLs
   - Local images use your server paths

3. **Template Usage**:
   ```html
   <!-- Automatically optimized based on context -->
   <img src="{{ team.get_logo_url('card') }}" alt="Team Logo">
   <img src="{{ team.get_logo_url('thumbnail') }}" alt="Team Thumbnail">
   ```

## 🛠️ Configuration Options

### In `config.py`:

```python
# ImageKit.io Configuration
IMAGEKIT_PRIVATE_KEY = os.environ.get('IMAGEKIT_PRIVATE_KEY')
IMAGEKIT_PUBLIC_KEY = os.environ.get('IMAGEKIT_PUBLIC_KEY') 
IMAGEKIT_URL_ENDPOINT = os.environ.get('IMAGEKIT_URL_ENDPOINT')

# Storage preference order: imagekit > github > local
PREFERRED_LOGO_STORAGE = os.environ.get('PREFERRED_LOGO_STORAGE', 'imagekit')
```

### Custom Transformations:

You can customize transformations in `imagekit_service.py`:

```python
# Add custom transformation contexts
transformations = {
    "custom": [
        {
            "height": "150",
            "width": "150",
            "crop": "maintain_ratio",
            "quality": "95",
            "format": "webp"
        }
    ]
}
```

## 🔍 Troubleshooting

### Common Issues

1. **"ImageKit service not configured" message**:
   - Verify environment variables are set correctly
   - Check that variable names match exactly
   - Restart your application after setting variables

2. **Images not loading**:
   - Check ImageKit URL endpoint format
   - Verify API keys have proper permissions
   - Check browser developer tools for error messages

3. **Migration fails**:
   - Ensure source images are accessible
   - Check ImageKit account limits and quotas
   - Verify network connectivity

### Debug Mode

Enable debug logging in `imagekit_service.py` by adding:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### Verify Configuration

Test your configuration with:

```python
from imagekit_service import imagekit_service
print("ImageKit configured:", imagekit_service.is_configured())
print("URL endpoint:", imagekit_service.url_endpoint)
```

## 📊 Performance Benefits

After switching to ImageKit.io, you should see:

- **50-70% faster** image loading times
- **30-50% smaller** file sizes due to optimization
- **Better SEO scores** from improved page load times
- **Improved user experience** with faster page rendering

## 🔐 Security Considerations

- **Private Key**: Never expose in client-side code or public repositories
- **Public Key**: Safe to use in frontend applications
- **URL Endpoint**: Safe to expose, used for image delivery

## 📝 Support

- **ImageKit Documentation**: [docs.imagekit.io](https://docs.imagekit.io)
- **Migration Issues**: Check `migrate_to_imagekit.py --help`
- **Service Status**: Monitor ImageKit dashboard for service health

## 🎉 Next Steps

1. **Monitor Performance**: Use browser dev tools to verify faster loading
2. **Optimize Further**: Experiment with different transformation contexts
3. **Implement Lazy Loading**: Consider adding lazy loading for better performance
4. **Set Up Monitoring**: Track image delivery metrics in ImageKit dashboard

Your application now supports fast, optimized image delivery with ImageKit.io! 🚀