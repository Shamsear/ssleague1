"""
ImageKit Service for Team Logo Management

This service handles uploading team logos to ImageKit.io and retrieving them
with real-time transformations for fast, optimized image delivery.
ImageKit.io provides better performance compared to GitHub for image hosting.
"""

import os
import base64
import mimetypes
from typing import Optional, Dict, Any, List
from datetime import datetime
import json
from imagekitio import ImageKit
from imagekitio.models.UploadFileRequestOptions import UploadFileRequestOptions

class ImageKitService:
    """Service for managing team logos using ImageKit.io"""
    
    def __init__(self):
        self.private_key = os.environ.get('IMAGEKIT_PRIVATE_KEY')
        self.public_key = os.environ.get('IMAGEKIT_PUBLIC_KEY')
        self.url_endpoint = os.environ.get('IMAGEKIT_URL_ENDPOINT')
        
        # Initialize ImageKit client
        if self.is_configured():
            self.imagekit = ImageKit(
                private_key=self.private_key,
                public_key=self.public_key,
                url_endpoint=self.url_endpoint,
            )
        else:
            self.imagekit = None
    
    def is_configured(self) -> bool:
        """Check if ImageKit service is properly configured"""
        return bool(self.private_key and self.public_key and self.url_endpoint)
    
    def upload_team_logo(self, team_id: int, team_name: str, logo_file_content: bytes, 
                        filename: str) -> Optional[Dict[str, Any]]:
        """
        Upload a team logo to ImageKit
        
        Args:
            team_id: Team's database ID
            team_name: Team name for organization
            logo_file_content: Binary content of the logo file
            filename: Original filename
            
        Returns:
            Dictionary with upload result or None if failed
        """
        if not self.is_configured():
            print("ImageKit service not configured")
            return None
        
        try:
            # Create a safe filename
            file_extension = filename.split('.')[-1].lower()
            safe_filename = f"team_{team_id}_{team_name.replace(' ', '_').lower()}.{file_extension}"
            
            # Path in ImageKit (folder structure)
            folder_path = "/team-logos"
            
            # Upload to ImageKit with basic options
            result = self.imagekit.upload_file(
                file=base64.b64encode(logo_file_content).decode('utf-8'),
                file_name=safe_filename,
                options=UploadFileRequestOptions(
                    folder=folder_path,
                    use_unique_file_name=False,
                    tags=["team-logo", f"team-{team_id}"]
                )
            )
            
            if result and hasattr(result, 'file_id'):
                # Extract data directly from the UploadFileResult object
                return {
                    'success': True,
                    'filename': safe_filename,
                    'file_id': result.file_id,
                    'url': result.url,
                    'thumbnail_url': getattr(result, 'thumbnail_url', None),
                    'file_path': getattr(result, 'file_path', None),
                    'tags': getattr(result, 'tags', []),
                    'size': getattr(result, 'size', 0),
                    'file_type': getattr(result, 'file_type', file_extension)
                }
            else:
                print(f"ImageKit upload failed: {result}")
                return None
                
        except Exception as e:
            print(f"Error uploading to ImageKit: {str(e)}")
            return None
    
    def get_logo_url(self, team_id: int, team_name: str, 
                    file_extension: str = 'png', 
                    transformations: List[Dict[str, Any]] = None) -> Optional[str]:
        """
        Get the optimized URL for a team's logo from ImageKit
        
        Args:
            team_id: Team's database ID
            team_name: Team name
            file_extension: File extension (png, jpg, etc.)
            transformations: List of ImageKit transformations to apply
            
        Returns:
            Optimized ImageKit URL or None if not found
        """
        if not self.is_configured():
            return None
        
        try:
            # Generate expected filename and path
            safe_filename = f"team_{team_id}_{team_name.replace(' ', '_').lower()}.{file_extension}"
            file_path = f"/team-logos/{safe_filename}"
            
            # Default transformations for optimization (no cropping)
            if transformations is None:
                transformations = [
                    {
                        "height": "100",
                        "width": "100",
                        "crop": "at_max",
                        "format": "auto",
                        "quality": "85"
                    }
                ]
            
            # Generate URL with transformations
            url = self.imagekit.url({
                "path": file_path,
                "transformation": transformations
            })
            
            return url
                
        except Exception as e:
            print(f"Error getting logo URL from ImageKit: {str(e)}")
            return None
    
    def get_logo_url_by_file_id(self, file_id: str, 
                               transformations: List[Dict[str, Any]] = None,
                               stored_url: str = None) -> Optional[str]:
        """
        Get the optimized URL using ImageKit file ID or stored URL
        
        Args:
            file_id: ImageKit file ID
            transformations: List of ImageKit transformations to apply
            stored_url: The stored ImageKit URL from database (preferred)
            
        Returns:
            Optimized ImageKit URL or None if not found
        """
        if not self.is_configured():
            return None
        
        try:
            # If we have a stored URL, extract the path from it
            if stored_url and stored_url.startswith(self.url_endpoint):
                # Extract path from stored URL
                file_path = stored_url.replace(self.url_endpoint, '')
            else:
                # Fallback: assume it's in team-logos folder with file ID
                file_path = f"/team-logos/{file_id}.png"
            
            # Default transformations for optimization (no cropping)
            if transformations is None:
                transformations = [
                    {
                        "height": "100",
                        "width": "100",
                        "crop": "at_max",
                        "format": "auto",
                        "quality": "85"
                    }
                ]
            
            # Convert transformation format for ImageKit URL API
            transform_params = []
            for transform in transformations:
                params = []
                if 'height' in transform:
                    params.append(f"h-{transform['height']}")
                if 'width' in transform:
                    params.append(f"w-{transform['width']}")
                if 'crop' in transform:
                    params.append(f"c-{transform['crop']}")
                if 'cropMode' in transform:
                    params.append(f"cm-{transform['cropMode']}")
                if 'quality' in transform:
                    params.append(f"q-{transform['quality']}")
                if 'format' in transform:
                    params.append(f"f-{transform['format']}")
                if 'radius' in transform:
                    params.append(f"r-{transform['radius']}")
                if 'background' in transform:
                    params.append(f"bg-{transform['background']}")
                
                if params:
                    transform_params.extend(params)
            
            # Generate URL with transformations using file path
            if transform_params:
                transformation_string = ','.join(transform_params)
                url = f"{self.url_endpoint}/tr:{transformation_string}{file_path}"
            else:
                url = f"{self.url_endpoint}{file_path}"
            
            return url
                
        except Exception as e:
            print(f"Error getting logo URL by file ID from ImageKit: {str(e)}")
            return None
    
    def delete_team_logo(self, file_id: str) -> bool:
        """
        Delete a team's logo from ImageKit
        
        Args:
            file_id: ImageKit file ID
            
        Returns:
            True if successful, False otherwise
        """
        if not self.is_configured():
            return False
        
        try:
            result = self.imagekit.delete_file(file_id)
            return result is not None
            
        except Exception as e:
            print(f"Error deleting logo from ImageKit: {str(e)}")
            return False
    
    def list_team_logos(self) -> List[Dict[str, Any]]:
        """
        List all team logos in ImageKit
        
        Returns:
            List of logo file information
        """
        if not self.is_configured():
            return []
        
        try:
            # List files in the team-logos folder
            result = self.imagekit.list_files({
                "path": "/team-logos",
                "search_query": 'name:"team_*"'
            })
            
            if result and hasattr(result, 'response_metadata'):
                files = result.response_metadata
                if isinstance(files, list):
                    return [
                        {
                            'file_id': file.get('fileId', file.get('file_id', '')),
                            'name': file.get('name', ''),
                            'file_path': file.get('filePath', file.get('file_path', '')),
                            'url': file.get('url', ''),
                            'thumbnail_url': file.get('thumbnailUrl', file.get('thumbnail_url')),
                            'size': file.get('size', 0),
                            'file_type': file.get('fileType', file.get('file_type', '')),
                            'created_at': file.get('createdAt', file.get('created_at', '')),
                            'tags': file.get('tags', [])
                        }
                        for file in files if isinstance(file, dict)
                    ]
            else:
                return []
                
        except Exception as e:
            print(f"Error listing logos from ImageKit: {str(e)}")
            return []
    
    def get_file_details(self, file_id: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a file
        
        Args:
            file_id: ImageKit file ID
            
        Returns:
            File details or None if not found
        """
        if not self.is_configured():
            return None
        
        try:
            result = self.imagekit.get_file_details(file_id)
            
            if result and hasattr(result, 'file_id'):
                # Direct access to file details
                return {
                    'file_id': result.file_id,
                    'name': getattr(result, 'name', ''),
                    'file_path': getattr(result, 'file_path', ''),
                    'url': getattr(result, 'url', ''),
                    'thumbnail_url': getattr(result, 'thumbnail_url', None),
                    'size': getattr(result, 'size', 0),
                    'file_type': getattr(result, 'file_type', ''),
                    'created_at': getattr(result, 'created_at', ''),
                    'updated_at': getattr(result, 'updated_at', None),
                    'tags': getattr(result, 'tags', []),
                    'custom_metadata': getattr(result, 'custom_metadata', {})
                }
            else:
                return None
                
        except Exception as e:
            print(f"Error getting file details from ImageKit: {str(e)}")
            return None
    
    def get_optimized_transformations(self, context: str = "thumbnail") -> List[Dict[str, Any]]:
        """
        Get predefined transformation sets for different use cases
        
        Args:
            context: Use case (thumbnail, card, hero, avatar)
            
        Returns:
            List of transformations optimized for the context
        """
        transformations = {
            "thumbnail": [
                {
                    "height": "50",
                    "width": "50",
                    "crop": "at_max",
                    "format": "auto",
                    "quality": "90"
                }
            ],
            "card": [
                {
                    "height": "100",
                    "width": "100",
                    "crop": "at_max", 
                    "format": "auto",
                    "quality": "85"
                }
            ],
            "hero": [
                {
                    "height": "200",
                    "width": "200",
                    "crop": "at_max", 
                    "format": "auto",
                    "quality": "90"
                }
            ],
            "avatar": [
                {
                    "height": "40",
                    "width": "40",
                    "crop": "at_max",
                    "format": "auto",
                    "quality": "85"
                }
            ],
            "full": [
                {
                    "format": "auto",
                    "quality": "90"
                }
            ]
        }
        
        return transformations.get(context, transformations["card"])

# Create a global instance
imagekit_service = ImageKitService()