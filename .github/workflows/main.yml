name: Parmar SSC Daily Downloader

on:
  workflow_dispatch:
  schedule:
    - cron: '15,30,45 3 * * 1-6'
    - cron: '0,15,30,45 4 * * 1-6'
    - cron: '0,15,30,45 5 * * 1-6'
    - cron: '0,15 6 * * 1-6'

jobs:
  download-and-upload:
    runs-on: ubuntu-latest
    outputs:
      new_video_json: ${{ steps.downloader.outputs.new_video_json }}
      
    steps:
      - name: Checkout repository
        uses: actions/checkout@v4
        with:
          token: ${{ secrets.GITHUB_TOKEN }}

      - name: Set up Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.10'

      - name: Install Dependencies
        run: |
          python -m pip install --upgrade pip
          pip install yt-dlp requests
          sudo apt-get update && sudo apt-get install -y rclone jq gh

      - name: Configure rclone
        run: |
          mkdir -p ~/.config/rclone
          echo "${{ secrets.RCLONE_CONF }}" > ~/.config/rclone/rclone.conf
        
      - name: Run Scraper and Downloader
        id: downloader
        env:
          YOUTUBE_API_KEY: ${{ secrets.YOUTUBE_API_KEY }}
          YOUTUBE_COOKIES: ${{ secrets.YOUTUBE_COOKIES }}
        run: |
          python downloader.py

      - name: Update videos.json database
        id: update_videos
        if: steps.downloader.outputs.new_video_json != '' && steps.downloader.outputs.new_video_json != 'null'
        run: |
          jq --argjson newVideo '${{ steps.downloader.outputs.new_video_json }}' '. + [$newVideo]' videos.json > temp.json && mv temp.json videos.json

      - name: Commit and push changes
        run: |
          git config --global user.name 'GitHub Actions Bot'
          git config --global user.email 'actions-bot@github.com'
          git add videos.json schedule.json live.json
          if ! git diff --staged --quiet; then
            git commit -m "feat: Update video library and schedule"
            git push
          else
            echo "No changes to commit."
          fi
          
      # --- NEW NOTIFICATION STEP ---
      - name: Create Issue on Authentication Failure
        if: steps.downloader.outputs.auth_error == 'true'
        env:
          GH_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        run: |
          gh issue create --title "Action Required: YouTube Cookies Have Expired" --body "The automatic downloader failed because the YouTube cookies are no longer valid. Please update the YOUTUBE_COOKIES secret in your repository settings to ensure future classes are recorded. This is a manual step that needs to be done every few days."
