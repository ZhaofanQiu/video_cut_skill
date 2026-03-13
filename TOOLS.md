# TOOLS.md - Local Notes

Skills define _how_ tools work. This file is for _your_ specifics — the stuff that's unique to your setup.

## What Goes Here

Things like:

- Camera names and locations
- SSH hosts and aliases
- Preferred voices for TTS
- Speaker/room names
- Device nicknames
- Anything environment-specific

## Examples

```markdown
### Cameras

- living-room → Main area, 180° wide angle
- front-door → Entrance, motion-triggered

### SSH

- home-server → 192.168.1.100, user: admin

### TTS

- Preferred voice: "Nova" (warm, slightly British)
- Default speaker: Kitchen HomePod
```

## Why Separate?

Skills are shared. Your setup is yours. Keeping them apart means you can update skills without losing your notes, and share skills without leaking your infrastructure.

---

Add whatever helps you do your job. This is your cheat sheet.

---

## Feishu File Transfer Notes

### Issue: MP4 Files Not Received

**Problem**: When sending `.mp4` video files via Feishu, the recipient does not receive them. However, `.mp3` audio files work fine.

**Root Cause**: Feishu has restrictions on `.mp4` file extensions in direct messages.

**Solution**: Change file extension to `.bin` (or other non-video extension) before sending.

### Workaround

```bash
# Rename MP4 to BIN before sending
cp video.mp4 video.bin

# Send video.bin via Feishu
# Recipient should rename back to .mp4 after download
```

### Testing

- ✅ `.mp3` - Works
- ❌ `.mp4` - Blocked
- ✅ `.bin` - Works (must rename after download)

### Notes

- This is a Feishu platform limitation, not a code issue
- Consider implementing automatic extension renaming for Feishu channel
- Document this for users in deployment guides
