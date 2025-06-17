from clearvoice import ClearVoice

class ClearVoiceAPI:
    def __init__(self):
        self.clearvoice = ClearVoice(task='speech_enhancement', model_names=['MossFormer2_SE_48K'])

    def enhance(self, input_path, output_path):
        # process single wave file
        output_wav = self.clearvoice(input_path=input_path, online_write=False)
        self.clearvoice.write(output_wav, output_path=output_path)
