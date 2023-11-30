import json
import os
import time
from datetime import datetime

import requests


def get_gist(
    gist_id=os.environ.get("GITHUB_GIST_ID", "ee9e4477069294141257acd6abc70463")
):
    """Get a gist with a file named "items.json" from GitHub."""
    print("Getting Item Cache from Gist:", gist_id)
    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    if os.environ.get("GITHUB_GIST_TOKEN"):
        headers["Authorization"] = f'Bearer {os.environ.get("GITHUB_GIST_TOKEN")}'

    attempt = 0
    max_attempts = 5
    response = None
    while attempt < max_attempts:
        try:
            response = requests.get(
                f"https://api.github.com/gists/{gist_id}", headers=headers
            )
            # If the request was successful, break out of the loop
            response.raise_for_status()
            data = response.json()
            file_data = data["files"]["items.json"]
            if file_data.get("truncated") and file_data.get("raw_url"):
                print("Using raw URL to fetch content...")
                # Fetch the raw content only if truncated is True
                raw_response = requests.get(file_data["raw_url"])
                raw_response.raise_for_status()
                print("Raw content fetched:", raw_response.text)
                return json.loads(raw_response.text)
            else:
                print("Using content from JSON response directly.")
                # If not truncated or raw_url doesn't exist, parse content directly
                print("Content from JSON response:", file_data["content"])
                return json.loads(file_data["content"])
        except requests.exceptions.RequestException as e:
            attempt += 1
            print(f"Attempt {attempt} failed, retrying in 3 seconds...")
            if attempt == max_attempts:
                # Raise the exception if the maximum number of attempts has been reached
                raise e
            # Wait before retrying
            time.sleep(3)

    print("Failed to fetch Item Cache Gist.")
    return {}


def update_gist(
    item_cache: dict,
    gist_id=os.environ.get("GITHUB_GIST_ID", "ee9e4477069294141257acd6abc70463"),
) -> str:
    """Update the gist with a file named "items.json" on GitHub."""
    if not os.environ.get("GITHUB_GIST_TOKEN"):
        print("No GitHub Token found, skipping updating online item cache.")
        return "The item cache was updated. *Gist was not updated, because no GitHub Token was found.*"

    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f'Bearer {os.environ.get("GITHUB_GIST_TOKEN")}',
        "X-GitHub-Api-Version": "2022-11-28",
        "Content-Type": "application/x-www-form-urlencoded",
    }

    content = json.dumps(item_cache, sort_keys=True, indent=2)
    data = {
        "description": f"Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "files": {"items.json": {"content": content}},
    }
    response = requests.patch(
        f"https://api.github.com/gists/{gist_id}", headers=headers, json=data
    )
    if response.status_code == 200:
        print("Successfully updated Item Cache Gist.")
        return "The item cache was updated. Gist was updated successfully."
    else:
        print("Failed to update Item Cache Gist:", response.text)
        return f"The item cache was updated. **Gist was not updated, because the update failed:** `{response.text}`"
