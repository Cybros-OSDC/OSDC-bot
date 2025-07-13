import aiohttp
import asyncio
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Union
from pathlib import Path

GITHUB_API_URL = "https://api.github.com"
GITHUB_SEARCH_URL = f"{GITHUB_API_URL}/search"

class GitHubAPI:
    def __init__(self, token: Optional[str] = None):
        self.token = token
        self.session = None
        self._session_lock = asyncio.Lock()
        
    async def __aenter__(self):
        async with self._session_lock:
            if self.session is None or self.session.closed:
                self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        async with self._session_lock:
            if self.session and not self.session.closed:
                await self.session.close()
                self.session = None
    
    async def _get_session(self):
        """Get or create a session safely"""
        async with self._session_lock:
            if self.session is None or self.session.closed:
                self.session = aiohttp.ClientSession()
            return self.session
    
    def _get_headers(self) -> Dict[str, str]:
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "Discord-Bot-CyBot"
        }
        if self.token:
            headers["Authorization"] = f"token {self.token}"
        return headers
    
    async def _make_request(self, url: str, params: Optional[Dict] = None) -> Optional[Dict]:
        """Make HTTP request with proper session management"""
        max_retries = 3
        for attempt in range(max_retries):
            try:
                session = await self._get_session()
                async with session.get(url, headers=self._get_headers(), params=params) as response:
                    if response.status == 200:
                        return await response.json()
                    elif response.status == 403:
                        print(f"Rate limit exceeded for {url}")
                        return None
                    else:
                        print(f"GitHub API error {response.status} for {url}")
                        return None
            except (aiohttp.ClientError, asyncio.TimeoutError) as e:
                print(f"Request failed (attempt {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
                    async with self._session_lock:
                        if self.session and not self.session.closed:
                            await self.session.close()
                        self.session = None
                else:
                    return None
        return None
    
    async def fetch_repo_events(self, repo: str, per_page: int = 10) -> List[Dict]:
        """Fetch recent events from a repository"""
        url = f"{GITHUB_API_URL}/repos/{repo}/events"
        params = {"per_page": per_page}
        data = await self._make_request(url, params)
        return data or []
    
    async def fetch_user_merged_prs(self, username: str, org: Optional[str] = None, 
                                   since: Optional[datetime] = None) -> int:
        """Fetch count of merged PRs for a user"""
        query = f"author:{username} is:pr is:merged"
        if org:
            query += f" org:{org}"
        if since:
            query += f" merged:>{since.isoformat()}"
        
        url = f"{GITHUB_SEARCH_URL}/issues"
        params = {"q": query, "per_page": 1}
        data = await self._make_request(url, params)
        return data.get("total_count", 0) if data else 0
    
    async def fetch_user_issues_opened(self, username: str, org: Optional[str] = None,
                                      since: Optional[datetime] = None) -> int:
        """Fetch count of issues opened by a user"""
        query = f"author:{username} is:issue"
        if org:
            query += f" org:{org}"
        if since:
            query += f" created:>{since.isoformat()}"
        
        url = f"{GITHUB_SEARCH_URL}/issues"
        params = {"q": query, "per_page": 1}
        data = await self._make_request(url, params)
        return data.get("total_count", 0) if data else 0
    
    async def fetch_user_info(self, username: str) -> Dict:
        """Fetch basic user information"""
        url = f"{GITHUB_API_URL}/users/{username}"
        data = await self._make_request(url)
        return data or {}
    
    async def fetch_user_repos(self, username: str) -> List[Dict]:
        """Fetch user's repositories"""
        url = f"{GITHUB_API_URL}/users/{username}/repos"
        params = {"per_page": 100, "sort": "updated"}
        data = await self._make_request(url, params)
        return data or []
    
    async def fetch_user_stats(self, username: str, org: Optional[str] = None) -> Dict:
        """Fetch comprehensive user statistics"""
        since_year = datetime.now() - timedelta(days=365)
        
        try:
            # Fetch user info
            user_info = await self.fetch_user_info(username)
            if not user_info:
                return {"username": username, "error": "User not found"}
            
            # Fetch repositories
            repos = await self.fetch_user_repos(username)
            
            # Calculate total stars
            total_stars = sum(repo.get("stargazers_count", 0) for repo in repos)
            
            # Fetch merged PRs
            merged_prs = await self.fetch_user_merged_prs(username, org, since_year)
            
            # Fetch issues opened
            issues_opened = await self.fetch_user_issues_opened(username, org, since_year)
            
            return {
                "username": username,
                "user_info": user_info,
                "total_stars": total_stars,
                "total_repos": len(repos),
                "merged_prs": merged_prs,
                "issues_opened": issues_opened,
                "repositories": repos,
                "updated_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            print(f"Error fetching stats for {username}: {e}")
            return {"username": username, "error": str(e)}

# Backward compatibility functions
def load_links(file_path: str = "github_links.json") -> Dict[int, str]:
    """Load GitHub links from JSON file"""
    try:
        if Path(file_path).exists():
            with open(file_path, 'r') as f:
                data = json.load(f)
                return {int(k): v for k, v in data.items()}
    except Exception as e:
        print(f"Error loading GitHub links: {e}")
    return {}

def save_links(links: Dict[int, str], file_path: str = "github_links.json"):
    """Save GitHub links to JSON file"""
    try:
        data = {str(k): v for k, v in links.items()}
        with open(file_path, 'w') as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"Error saving GitHub links: {e}")

async def get_github_stars(username: str, token: Optional[str] = None) -> int:
    """Get total GitHub stars for a user"""
    async with GitHubAPI(token) as api:
        stats = await api.fetch_user_stats(username)
        return stats.get("total_stars", 0)

async def get_github_repos(username: str, token: Optional[str] = None) -> int:
    """Get total repository count for a user"""
    async with GitHubAPI(token) as api:
        stats = await api.fetch_user_stats(username)
        return stats.get("total_repos", 0)

async def fetch_user_stats(username: str, token: Optional[str] = None, org: Optional[str] = None) -> Dict:
    """Fetch user stats (backward compatibility)"""
    async with GitHubAPI(token) as api:
        return await api.fetch_user_stats(username, org)

async def fetch_repo_events(repo: str, token: Optional[str] = None) -> List[Dict]:
    """Fetch repository events (backward compatibility)"""
    async with GitHubAPI(token) as api:
        return await api.fetch_repo_events(repo)
