import os
import subprocess

# 1. Timeline configuration matching your storyboard
SCENE_TIMINGS = [
    {"file": "scene1.mp4", "duration": 45},
    {"file": "scene2.mp4", "duration": 45},
    {"file": "scene3.mp4", "duration": 60},
    {"file": "scene4.mp4", "duration": 60},
    {"file": "scene5.mp4", "duration": 60},
    {"file": "scene6.mp4", "duration": 45},
    {"file": "scene7.mp4", "duration": 35},
]

VOICEOVER = "voiceover.wav"
BGM = "bg_music.mp3"
OUTPUT = "EduCore_AI_Final_Master.mp4"

def run_cmd(cmd):
    print(f"Executing: {cmd}")
    subprocess.run(cmd, shell=True, check=True)

def main():
    normalized_clips = []
    
    # Standardize resolution (1080p), framerate (30fps), and clip durations
    for idx, item in enumerate(SCENE_TIMINGS):
        src = item["file"]
        dur = item["duration"]
        norm_out = f"norm_{idx+1}.mp4"
        
        # Scale/pad to 1080p, conform to 30fps, trim exact duration
        cmd = (
            f"ffmpeg -y -i {src} -t {dur} -vf "
            f"\"scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2,fps=30\" "
            f"-c:v libx264 -crf 18 -preset fast -an {norm_out}"
        )
        run_cmd(cmd)
        normalized_clips.append(norm_out)

    # Write concat manifest
    with open("clips.txt", "w") as f:
        for clip in normalized_clips:
            f.write(f"file '{clip}'\n")

    # Final pass: Concatenate visuals and mix sidechain audio
    final_cmd = (
        f"ffmpeg -y -f concat -safe 0 -i clips.txt -i {VOICEOVER} -i {BGM} "
        f"-filter_complex \""
        f"[2:a]volume=0.30[music]; "
        f"[music][1:a]sidechaincompress=threshold=0.06:ratio=6:attack=15:release=350[ducked]; "
        f"[ducked][1:a]amix=inputs=2:weights=1 1.2:dropout_transition=2[outa]\" "
        f"-map 0:v -map \"[outa]\" "
        f"-c:v copy -c:a aac -b:a 320k -shortest {OUTPUT}"
    )
    run_cmd(final_cmd)

    # Cleanup temporary normalized files
    for clip in normalized_clips:
        os.remove(clip)
    os.remove("clips.txt")

    print(f"\n Master output generated: {OUTPUT}")

if __name__ == "__main__":
    main()