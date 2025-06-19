import glob
import hashlib
import re
import requests

from flask import Flask, render_template, request, jsonify, send_from_directory, abort
from moviepy.video.io.VideoFileClip import VideoFileClip

from utils.seam import *
from video import get_video

app = Flask(__name__)

DOWNLOAD_DIR = os.path.join(os.getcwd(), 'downloads')
# 确保下载目录存在
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

# 用于跟踪视频片段的字典
video_segments = {}

# 视频缓存
video_cache = {}


def get_video_hash(url):
    """生成视频URL的哈希值作为缓存键"""
    return hashlib.md5(url.encode()).hexdigest()


@app.route('/downloads/<path:filename>')
def downloads(filename):
    requested_path = os.path.abspath(os.path.join(DOWNLOAD_DIR, filename))
    if not requested_path.startswith(DOWNLOAD_DIR):
        abort(404)
    return send_from_directory(DOWNLOAD_DIR, filename)


@app.route('/', methods=['GET', 'POST'])
def index():
    input_data = None
    if request.method == 'POST':
        input_data = {
            'url': request.form.get('user_input'),
            'start': request.form.get('start_time'),
            'end': request.form.get('end_time')
        }
    return render_template('index.html', input_data=input_data)


@app.route('/api/preview_video', methods=['POST'])
def preview_video():
    try:
        data = request.get_json()
        video_url = data.get('url')

        if not video_url:
            return jsonify({'error': '缺少视频URL参数'}), 400

        # 检查缓存
        video_hash = get_video_hash(video_url)
        if video_hash in video_cache:
            return jsonify(video_cache[video_hash])

        # 获取视频信息
        title = get_video(video_url)
        safe_title = re.sub(r'[\\/:"*?<>|]+', '', title)
        filename = f"{safe_title}.mp4"
        video_path = os.path.join(DOWNLOAD_DIR, filename)

        if not os.path.exists(video_path):
            return jsonify({'error': '视频文件不存在'}), 500

        # 初始化视频片段跟踪
        if safe_title not in video_segments:
            video_segments[safe_title] = {
                'original_path': video_path,
                'segments': []
            }

        response_data = {
            'title': title,
            'video_url': f'/downloads/{filename}'
        }

        # 更新缓存
        video_cache[video_hash] = response_data

        return jsonify(response_data)

    except requests.RequestException as e:
        return jsonify({'error': f'请求B站失败: {str(e)}'}), 502
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': f'服务器错误: {str(e)}'}), 500


@app.route('/api/get_segments', methods=['POST'])
def get_segments():
    try:
        data = request.get_json()
        title = data.get('title')
        safe_title = re.sub(r'[\\/:"*?<>|]+', '', title)

        if safe_title not in video_segments:
            return jsonify({'segments': []})

        segments = []
        for segment in video_segments[safe_title]['segments']:
            # 从文件名中提取时间信息
            filename = os.path.basename(segment)
            time_match = re.search(r'_(\d+)-(\d+)_', filename)
            if time_match:
                start_time = float(time_match.group(1))
                end_time = float(time_match.group(2))
                segments.append({
                    'title': title,
                    'start': start_time,
                    'end': end_time,
                    'url': f'/downloads/{os.path.basename(segment)}'
                })

        return jsonify({'segments': segments})

    except Exception as e:
        return jsonify({'error': f'获取片段列表失败: {str(e)}'}), 500


@app.route('/api/finish_download', methods=['POST'])
def finish_download():
    try:
        data = request.get_json()
        title = data.get('title')
        if not title:
            return jsonify({'error': '缺少标题参数'}), 400

        safe_title = re.sub(r'[\\/:"*?<>|]+', '', title)

        if safe_title not in video_segments:
            return jsonify({'error': '未找到视频信息'}), 404

        video_info = video_segments[safe_title]
        original_path = video_info.get('original_path')

        # 删除原始文件
        if original_path and os.path.exists(original_path):
            try:
                os.remove(original_path)
                print(f"删除原始视频文件: {original_path}")
            except Exception as e:
                return jsonify({'error': f'删除原始视频失败: {str(e)}'}), 500

        # 批量删除相关片段文件，假设在original_path同目录
        if original_path:
            directory = os.path.dirname(original_path)
            pattern = os.path.join(directory, f"{safe_title}_*.mp4")
            for filepath in glob.glob(pattern):
                try:
                    os.remove(filepath)
                    print(f"删除片段文件: {filepath}")
                except Exception as e:
                    print(f"删除片段文件失败: {filepath}, 错误: {e}")

        # 删除记录
        video_segments.pop(safe_title, None)

        # 清理视频缓存，建议这里也用 safe_title 比较
        for url_hash, cache_data in list(video_cache.items()):
            if re.sub(r'[\\/:"*?<>|]+', '', cache_data.get('title', '')) == safe_title:
                del video_cache[url_hash]

        return jsonify({'message': '完成当前下载，点击重置继续下载'})

    except Exception as e:
        return jsonify({'error': f'操作失败: {str(e)}'}), 500


@app.route('/api/get_video', methods=['POST'])
def video_api():
    try:
        data = request.get_json()
        video_url = data.get('url')
        start_time = data.get('start')
        end_time = data.get('end')

        if not video_url:
            return jsonify({'error': '缺少视频URL参数'}), 400

        title = get_video(video_url)
        safe_title = re.sub(r'[\\/:"*?<>|]+', '', title)
        filename = f"{safe_title}.mp4"
        video_path = os.path.join(DOWNLOAD_DIR, filename)

        if not os.path.exists(video_path):
            return jsonify({'error': '视频文件不存在，合并可能失败'}), 500

        # 如果提供了时间，剪辑片段
        if start_time is not None and end_time is not None:
            clip_filename = f"{safe_title}_{start_time}-{end_time}.mp4"
            clip_path = os.path.join(DOWNLOAD_DIR, clip_filename)

            try:
                start = float(start_time)
                end = float(end_time)

                with VideoFileClip(video_path) as clip:
                    subclip = clip.subclip(start, end)
                    subclip.write_videofile(
                        clip_path,
                        codec="libx264",
                        audio_codec="aac",
                        threads=4,
                        preset="ultrafast",
                        fps=clip.fps,
                        logger=None  # 不输出冗余信息
                    )

                return jsonify({
                    'title': title,
                    'video_url': f'/downloads/{clip_filename}'
                })
            except Exception as e:
                return jsonify({'error': f'剪辑失败: {str(e)}'}), 500

        # 没有时间参数，返回完整视频
        return jsonify({
            'title': title,
            'video_url': f'/downloads/{filename}'
        })

    except requests.RequestException as e:
        return jsonify({'error': f'请求B站失败: {str(e)}'}), 502
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': f'服务器错误: {str(e)}'}), 500


@app.route('/api/video_process', methods=['POST'])
def video_process():
    data = request.get_json()
    action = data.get('action')

    if not action:
        return jsonify({'success': False, 'message': '缺少 action 参数'}), 400

    # 自动查找 /downloads/ 目录下最新的 mp4 文件
    mp4_files = glob.glob(os.path.join(DOWNLOAD_DIR, '*.mp4'))
    if not mp4_files:
        return jsonify({'success': False, 'message': '未找到可处理的视频文件'}), 404

    # 取最后修改时间最新的文件
    mp4_files.sort(key=os.path.getmtime, reverse=True)
    local_path = mp4_files[0]
    print(f"[自动选择] 最新视频文件: {local_path}")

    try:
        if action == 'vocal_remove':
            output_audio_path = os.path.join(DOWNLOAD_DIR, 'vocal_removed.wav')
            success = vocal_remove(local_path, output_audio_path)
            return jsonify({
                'success': success,
                'message': f"伴奏提取 {'成功' if success else '失败'}",
                'file_path': f'/downloads/{os.path.basename(output_audio_path)}'
            })

        elif action == 'extract_subtitle':
            output_srt_path = os.path.join(DOWNLOAD_DIR, 'subtitle.srt')
            success = extract_subtitle(local_path, output_srt_path)
            return jsonify({
                'success': success,
                'message': f"字幕提取 {'成功' if success else '失败'}",
                'file_path': f'/downloads/{os.path.basename(output_srt_path)}'
            })

        elif action == 'enhance_audio':
            output_video_path = os.path.join(DOWNLOAD_DIR, 'video_enhanced.mp4')
            success = enhance_video_audio(local_path, output_video_path)
            return jsonify({
                'success': success,
                'message': f"人声增强 {'成功' if success else '失败'}",
                'file_path': f'/downloads/{os.path.basename(output_video_path)}'
            })

        else:
            return jsonify({'success': False, 'message': '未知操作类型'}), 400

    except Exception as e:
        return jsonify({'success': False, 'message': f'处理异常: {str(e)}'}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
