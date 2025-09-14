#!/usr/bin/env python3
"""
Migration utility to transfer team logos from GitHub to ImageKit.io

This script migrates existing team logos from GitHub storage to ImageKit.io
for better performance and image optimization capabilities.

Usage:
    python migrate_to_imagekit.py --dry-run  # Preview what would be migrated
    python migrate_to_imagekit.py            # Perform the migration
    python migrate_to_imagekit.py --force    # Force migration even if ImageKit already has images
"""

import os
import sys
import argparse
import requests
from datetime import datetime

# Add the current directory to Python path so we can import our modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app
from models import db, Team
from github_service import github_service
from imagekit_service import imagekit_service

def download_image_from_url(url):
    """Download image content from a URL"""
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        return response.content
    except Exception as e:
        print(f"Error downloading image from {url}: {e}")
        return None

def migrate_team_logo(team, dry_run=False, force=False):
    """Migrate a single team's logo from GitHub to ImageKit"""
    
    # Skip if team doesn't have a GitHub logo
    if team.logo_storage_type != 'github' or not team.logo_url:
        return False, "No GitHub logo to migrate"
    
    # Skip if already on ImageKit (unless forced)
    if team.logo_storage_type == 'imagekit' and team.imagekit_file_id and not force:
        return False, "Already on ImageKit"
    
    print(f"\n{'[DRY RUN] ' if dry_run else ''}Migrating logo for team: {team.name} (ID: {team.id})")
    print(f"  Current URL: {team.logo_url}")
    
    if dry_run:
        return True, "Would migrate (dry run)"
    
    try:
        # Download the image from GitHub
        print("  Downloading image from GitHub...")
        image_content = download_image_from_url(team.logo_url)
        
        if not image_content:
            return False, "Failed to download image from GitHub"
        
        # Extract filename from URL or create a default one
        filename = team.logo_url.split('/')[-1] if '/' in team.logo_url else f"team_{team.id}_logo.png"
        
        # Upload to ImageKit
        print("  Uploading to ImageKit...")
        result = imagekit_service.upload_team_logo(
            team.id,
            team.name,
            image_content,
            filename
        )
        
        if result and result.get('success'):
            # Update the team record
            old_url = team.logo_url
            team.logo_storage_type = 'imagekit'
            team.imagekit_file_id = result.get('file_id')
            team.logo_url = result.get('url')
            
            # Keep GitHub SHA for potential rollback
            # team.github_logo_sha remains unchanged
            
            db.session.commit()
            
            print(f"  ✅ Successfully migrated!")
            print(f"    Old URL: {old_url}")
            print(f"    New URL: {team.logo_url}")
            print(f"    File ID: {team.imagekit_file_id}")
            
            return True, "Successfully migrated to ImageKit"
        else:
            return False, f"ImageKit upload failed: {result}"
            
    except Exception as e:
        return False, f"Migration error: {str(e)}"

def main():
    parser = argparse.ArgumentParser(description='Migrate team logos from GitHub to ImageKit')
    parser.add_argument('--dry-run', action='store_true', help='Preview migration without making changes')
    parser.add_argument('--force', action='store_true', help='Force migration even if already on ImageKit')
    parser.add_argument('--team-id', type=int, help='Migrate only a specific team ID')
    
    args = parser.parse_args()
    
    # Check if services are configured
    if not imagekit_service.is_configured():
        print("❌ ImageKit service is not configured!")
        print("Please set the following environment variables:")
        print("  IMAGEKIT_PRIVATE_KEY")
        print("  IMAGEKIT_PUBLIC_KEY")
        print("  IMAGEKIT_URL_ENDPOINT")
        return 1
    
    if not github_service.is_configured():
        print("⚠️  GitHub service is not configured - this is OK if you only have local images")
    
    print(f"🚀 {'DRY RUN: ' if args.dry_run else ''}Starting migration from GitHub to ImageKit")
    print(f"   ImageKit URL: {imagekit_service.url_endpoint}")
    
    with app.app_context():
        # Get teams to migrate
        if args.team_id:
            teams = Team.query.filter_by(id=args.team_id).all()
            if not teams:
                print(f"❌ Team with ID {args.team_id} not found")
                return 1
        else:
            teams = Team.query.filter_by(logo_storage_type='github').all()
        
        if not teams:
            print("ℹ️  No teams with GitHub logos found to migrate")
            return 0
        
        print(f"Found {len(teams)} team(s) with GitHub logos")
        
        success_count = 0
        skip_count = 0
        error_count = 0
        
        for team in teams:
            try:
                success, message = migrate_team_logo(team, dry_run=args.dry_run, force=args.force)
                
                if success:
                    success_count += 1
                elif "Already on ImageKit" in message or "Would migrate" in message:
                    skip_count += 1
                    print(f"  ⏭️  Skipped: {message}")
                else:
                    error_count += 1
                    print(f"  ❌ Failed: {message}")
                    
            except Exception as e:
                error_count += 1
                print(f"  ❌ Unexpected error for team {team.name}: {e}")
        
        print(f"\n📊 Migration {'preview' if args.dry_run else 'results'}:")
        print(f"  ✅ {'Would migrate' if args.dry_run else 'Migrated'}: {success_count}")
        print(f"  ⏭️  Skipped: {skip_count}")
        print(f"  ❌ Errors: {error_count}")
        
        if args.dry_run and success_count > 0:
            print(f"\n💡 To perform the actual migration, run:")
            print(f"   python migrate_to_imagekit.py")
        
        return 0 if error_count == 0 else 1

if __name__ == '__main__':
    sys.exit(main())