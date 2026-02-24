#!/bin/bash
# Auto-start Cloudflare tunnel, update Expo env, restart Expo with correct URL
# Stored in /app/ so it persists across container restarts

LOG=/var/log/supervisor/cloudflared.out.log
URL_FILE=/tmp/tunnel_url.txt
ENV_FILE=/app/frontend/.env
CF_BIN=/app/cloudflared

# Download binary if missing (e.g. after OS-level wipe)
if [ ! -f "$CF_BIN" ]; then
  echo "[tunnel] Downloading cloudflared binary..."
  curl -sL https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-arm64 -o $CF_BIN
  chmod +x $CF_BIN
fi

echo "" > $URL_FILE
echo "[tunnel] Starting cloudflared tunnel to localhost:3000..."

EXPO_UPDATED=0

/app/cloudflared tunnel --url http://localhost:3000 2>&1 | while IFS= read -r line; do
  echo "$line"
  # Extract tunnel URL when it appears
  if echo "$line" | grep -qE "https://[a-z0-9-]+\.trycloudflare\.com"; then
    URL=$(echo "$line" | grep -oE "https://[a-z0-9-]+\.trycloudflare\.com" | head -1)
    if [ -n "$URL" ] && [ "$EXPO_UPDATED" = "0" ]; then
      HOSTNAME=$(echo "$URL" | sed 's|https://||')
      echo "$URL" > $URL_FILE

      # Update Expo env to use this tunnel
      if grep -q "EXPO_PACKAGER_PROXY_URL" $ENV_FILE; then
        sed -i "s|EXPO_PACKAGER_PROXY_URL=.*|EXPO_PACKAGER_PROXY_URL=$URL|" $ENV_FILE
      else
        echo "EXPO_PACKAGER_PROXY_URL=$URL" >> $ENV_FILE
      fi
      if grep -q "REACT_NATIVE_PACKAGER_HOSTNAME" $ENV_FILE; then
        sed -i "s|REACT_NATIVE_PACKAGER_HOSTNAME=.*|REACT_NATIVE_PACKAGER_HOSTNAME=$HOSTNAME|" $ENV_FILE
      else
        echo "REACT_NATIVE_PACKAGER_HOSTNAME=$HOSTNAME" >> $ENV_FILE
      fi

      echo "[tunnel] Active URL: $URL"
      echo "[tunnel] Expo Go QR URL: exp://$HOSTNAME"
      echo "[tunnel] Updated frontend/.env"

      # Restart Expo to pick up the new tunnel URL
      sleep 3
      supervisorctl restart expo
      echo "[tunnel] Expo restarted with new tunnel URL"
      EXPO_UPDATED=1
    fi
  fi
done
