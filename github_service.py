"""
GitHub Service for Team Logo Management

This service handles uploading team logos to a GitHub repository and retrieving them
for display on web pages. It provides a centralized way to manage team assets
using GitHub as a storage backend.
"""

import os
import base64
import requests
from typing import Optional, Dict, Any, List
from datetime import datetime
import json
from config import Config

class GitHubService:
    """Service for managing team logos in GitHub repository"""
    
    def __init__(self):
        self.github_token = os.environ.get('GITHUB_TOKEN')
        self.repo_owner = os.environ.get('GITHUB_REPO_OWNER', 'your-org')
        self.repo_name = os.environ.get('GITHUB_REPO_NAME', 'team-logos')
        self.base_url = 'https://api.github.com'
        self.base_branch = os.environ.get('GITHUB_BRANCH', 'main')
        
        # Headers for GitHub API
        self.headers = {
            'Authorization': f'token {self.github_token}',
            'Accept': 'application/vnd.github.v3+json',
            'Content-Type': 'application/json',
        }
    
    def is_configured(self) -> bool:
        """Check if GitHub service is properly configured"""
        return bool(self.github_token and self.repo_owner and self.repo_name)
    
    def upload_team_logo(self, team_id: int, team_name: str, logo_file_content: bytes, 
                        filename: str) -> Optional[Dict[str, Any]]:
        """
        Upload a team logo to GitHub repository
        
        Args:
            team_id: Team's database ID
            team_name: Team name for organization
            logo_file_content: Binary content of the logo file
            filename: Original filename
            
        Returns:
            Dictionary with upload result or None if failed
        """
        if not self.is_configured():
            print("GitHub service not configured")
            return None
        
        try:
            # Create a safe filename
            file_extension = filename.split('.')[-1].lower()
            safe_filename = f"team_{team_id}_{team_name.replace(' ', '_').lower()}.{file_extension}"
            
            # Path in repository
            repo_path = f"logos/{safe_filename}"
            
            # Encode file content to base64
            encoded_content = base64.b64encode(logo_file_content).decode('utf-8')
            
            # Check if file already exists to get SHA for update
            existing_file_sha = self._get_file_sha(repo_path)
            
            # Prepare the commit data
            commit_data = {
                'message': f'Upload logo for team: {team_name}',
                'content': encoded_content,
                'branch': self.base_branch
            }
            
            # If file exists, include SHA for update
            if existing_file_sha:
                commit_data['sha'] = existing_file_sha
            
            # Make API request to create/update file
            url = f"{self.base_url}/repos/{self.repo_owner}/{self.repo_name}/contents/{repo_path}"
            response = requests.put(url, headers=self.headers, json=commit_data)
            
            if response.status_code in [200, 201]:
                result = response.json()
                return {
                    'success': True,
                    'filename': safe_filename,
                    'path': repo_path,
                    'download_url': result['content']['download_url'],
                    'html_url': result['content']['html_url'],
                    'sha': result['content']['sha']
                }
            else:
                print(f"GitHub upload failed: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            print(f"Error uploading to GitHub: {str(e)}")
            return None
    
    def get_logo_url(self, team_id: int, team_name: str, file_extension: str = 'png') -> Optional[str]:
        """
        Get the download URL for a team's logo from GitHub
        
        Args:
            team_id: Team's database ID
            team_name: Team name
            file_extension: File extension (png, jpg, etc.)
            
        Returns:
            Download URL or None if not found
        """
        if not self.is_configured():
            return None
        
        try:
            # Generate expected filename
            safe_filename = f"team_{team_id}_{team_name.replace(' ', '_').lower()}.{file_extension}"
            repo_path = f"logos/{safe_filename}"
            
            # Get file info from GitHub
            url = f"{self.base_url}/repos/{self.repo_owner}/{self.repo_name}/contents/{repo_path}"
            response = requests.get(url, headers=self.headers)
            
            if response.status_code == 200:
                file_info = response.json()
                return file_info['download_url']
            else:
                return None
                
        except Exception as e:
            print(f"Error getting logo URL from GitHub: {str(e)}")
            return None
    
    def delete_team_logo(self, team_id: int, team_name: str, file_extension: str = 'png') -> bool:
        """
        Delete a team's logo from GitHub repository
        
        Args:
            team_id: Team's database ID
            team_name: Team name
            file_extension: File extension
            
        Returns:
            True if successful, False otherwise
        """
        if not self.is_configured():
            return False
        
        try:
            # Generate expected filename
            safe_filename = f"team_{team_id}_{team_name.replace(' ', '_').lower()}.{file_extension}"
            repo_path = f"logos/{safe_filename}"
            
            # Get current file SHA
            file_sha = self._get_file_sha(repo_path)
            if not file_sha:
                return False  # File doesn't exist
            
            # Delete the file
            url = f"{self.base_url}/repos/{self.repo_owner}/{self.repo_name}/contents/{repo_path}"
            delete_data = {
                'message': f'Delete logo for team: {team_name}',
                'sha': file_sha,
                'branch': self.base_branch
            }
            
            response = requests.delete(url, headers=self.headers, json=delete_data)
            return response.status_code == 200
            
        except Exception as e:
            print(f"Error deleting logo from GitHub: {str(e)}")
            return False
    
    def list_team_logos(self) -> List[Dict[str, Any]]:
        """
        List all team logos in the repository
        
        Returns:
            List of logo file information
        """
        if not self.is_configured():
            return []
        
        try:
            url = f"{self.base_url}/repos/{self.repo_owner}/{self.repo_name}/contents/logos"
            response = requests.get(url, headers=self.headers)
            
            if response.status_code == 200:
                files = response.json()
                return [
                    {
                        'name': file['name'],
                        'path': file['path'],
                        'download_url': file['download_url'],
                        'size': file['size']
                    }
                    for file in files if file['type'] == 'file'
                ]
            else:
                return []
                
        except Exception as e:
            print(f"Error listing logos from GitHub: {str(e)}")
            return []
    
    def _get_file_sha(self, repo_path: str) -> Optional[str]:
        """
        Get the SHA hash of a file in the repository
        
        Args:
            repo_path: Path to the file in the repository
            
        Returns:
            SHA hash or None if file doesn't exist
        """
        try:
            url = f"{self.base_url}/repos/{self.repo_owner}/{self.repo_name}/contents/{repo_path}"
            response = requests.get(url, headers=self.headers)
            
            if response.status_code == 200:
                file_info = response.json()
                return file_info['sha']
            else:
                return None
                
        except Exception as e:
            return None
    
    def create_repository_if_not_exists(self) -> bool:
        """
        Create the logos repository if it doesn't exist
        
        Returns:
            True if repository exists or was created successfully
        """
        if not self.is_configured():
            return False
        
        try:
            # Check if repository exists
            url = f"{self.base_url}/repos/{self.repo_owner}/{self.repo_name}"
            response = requests.get(url, headers=self.headers)
            
            if response.status_code == 200:
                return True  # Repository exists
            
            # Create repository
            create_data = {
                'name': self.repo_name,
                'description': 'Team logos storage for the sports management system',
                'private': False,  # Change to True if you want private repo
                'auto_init': True,
                'gitignore_template': None,
                'license_template': None
            }
            
            if self.repo_owner != self._get_authenticated_user():
                # Creating in organization
                create_url = f"{self.base_url}/orgs/{self.repo_owner}/repos"
            else:
                # Creating in personal account
                create_url = f"{self.base_url}/user/repos"
            
            response = requests.post(create_url, headers=self.headers, json=create_data)
            return response.status_code == 201
            
        except Exception as e:
            print(f"Error creating repository: {str(e)}")
            return False
    
    def _get_authenticated_user(self) -> Optional[str]:
        """Get the username of the authenticated user"""
        try:
            url = f"{self.base_url}/user"
            response = requests.get(url, headers=self.headers)
            
            if response.status_code == 200:
                user_info = response.json()
                return user_info['login']
            else:
                return None
                
        except Exception as e:
            return None

# Create a global instance
github_service = GitHubService()
