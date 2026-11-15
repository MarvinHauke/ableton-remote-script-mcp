from live_model.model import ModelObject, ValueProperty


class Song(ModelObject):
    tempo = ValueProperty()
    file_path = ValueProperty(writeable=False)

    def stop_playing(self):
        pass
