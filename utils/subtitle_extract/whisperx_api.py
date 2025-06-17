import whisperx

def convert_seg_to_srt(subtitles):
    srt_content = []
    for i, entry in enumerate(subtitles, start=1):
        # 格式化开始时间
        start_sec = entry['start']
        start_h = int(start_sec // 3600)
        start_m = int((start_sec % 3600) // 60)
        start_s = int(start_sec % 60)
        start_ms = int((start_sec - int(start_sec)) * 1000)
        start_time = f"{start_h:02d}:{start_m:02d}:{start_s:02d},{start_ms:03d}"

        # 格式化结束时间
        end_sec = entry['end']
        end_h = int(end_sec // 3600)
        end_m = int((end_sec % 3600) // 60)
        end_s = int(end_sec % 60)
        end_ms = int((end_sec - int(end_sec)) * 1000)
        end_time = f"{end_h:02d}:{end_m:02d}:{end_s:02d},{end_ms:03d}"

        # 构建字幕块
        srt_content.append(str(i))
        srt_content.append(f"{start_time} --> {end_time}")
        srt_content.append(entry['text'])
        srt_content.append("")  # 空行分隔

    return "\n".join(srt_content)


def convert_words_to_srt(segments):
    def format_time(seconds):
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        seconds_remainder = seconds % 60
        milliseconds = int((seconds_remainder - int(seconds_remainder)) * 1000)
        return f"{hours:02d}:{minutes:02d}:{int(seconds_remainder):02d},{milliseconds:03d}"

    srt_lines = []
    segment_index = 1

    for segment in segments:
        words = segment['words']
        current_line = []
        current_start = None
        current_end = None

        for word in words:
            # 处理没有时间信息的词（如数字、符号）
            if 'start' not in word or 'end' not in word:
                current_line.append(word['word'])
                continue

            word_start = word['start']
            word_end = word['end']

            # 初始化当前行
            if not current_line:
                current_line.append(word['word'])
                current_start = word_start
                current_end = word_end
                continue

            # 计算加入新词后的持续时间
            new_duration = word_end - current_start

            # 如果加入新词后持续时间 <= 5秒，则添加到当前行
            if new_duration <= 5:
                current_line.append(word['word'])
                current_end = word_end
            else:
                # 如果当前行持续时间 < 3秒，强制添加新词（即使超过5秒）
                current_duration = current_end - current_start
                if current_duration < 3:
                    current_line.append(word['word'])
                    current_end = word_end
                else:
                    # 结束当前行并添加到输出
                    srt_lines.append({
                        'index': segment_index,
                        'start': current_start,
                        'end': current_end,
                        'text': ''.join(current_line)
                    })
                    segment_index += 1

                    # 开始新行
                    current_line = [word['word']]
                    current_start = word_start
                    current_end = word_end

        # 处理段落的最后一行
        if current_line:
            srt_lines.append({
                'index': segment_index,
                'start': current_start if current_start is not None else segment['start'],
                'end': current_end if current_end is not None else segment['end'],
                'text': ''.join(current_line)
            })
            segment_index += 1

    # 生成SRT格式字符串
    srt_output = []
    for line in srt_lines:
        start_time = format_time(line['start'])
        end_time = format_time(line['end'])
        srt_output.append(f"{line['index']}")
        srt_output.append(f"{start_time} --> {end_time}")
        srt_output.append(line['text'])
        srt_output.append("")

    return "\n".join(srt_output)

class WhisperXAPI:
    def __init__(self):
        device_id = "cuda"
        model_version = "large-v3"
        self.model = whisperx.load_model(model_version, device_id, language="zh")

    def transcribe(self, audio_path, batch_size=16):
        audio = whisperx.load_audio(audio_path)
        result = self.model.transcribe(audio, batch_size=batch_size)
        model_a, metadata = whisperx.load_align_model(language_code=result["language"], device="cuda")
        result = whisperx.align(result["segments"], model_a, metadata, audio, "cuda", return_char_alignments=False)
        # print(convert_words_to_srt(result["segments"]))

        return convert_words_to_srt(result["segments"])


if __name__ == '__main__':
    device_id = "cuda"
    batch_size = 16
    model_version = "large-v3"

    audio_file = "../media_files/test_video.mp4"

    model = whisperx.load_model(model_version, device_id, language="zh")
    audio = whisperx.load_audio(audio_file)
    result = model.transcribe(audio, batch_size=batch_size)

    print(result["segments"]) # before alignment
    print(convert_seg_to_srt(result["segments"]))

    model_a, metadata = whisperx.load_align_model(language_code=result["language"], device="cuda")
    result = whisperx.align(result["segments"], model_a, metadata, audio, "cuda", return_char_alignments=False)
    print(result["segments"])  # after alignment
    print(convert_words_to_srt(result["segments"]))