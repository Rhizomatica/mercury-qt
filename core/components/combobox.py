from PySide6 import QtWidgets, QtCore

class ComboBox(QtWidgets.QWidget):
    # NOVO: Sinal que emitirá o dicionário de comando já formatado
    command_to_send = QtCore.Signal(dict) 

    def __init__(self, key: str, parent=None):
        super().__init__(parent)
        
        # NOVO: Guarda a chave para formatar o comando (ex: "soundcard" ou "radio")
        self.key = key 
        
        # Inicializa o QComboBox
        self.combo_box = QtWidgets.QComboBox()
        
        # Conecta o sinal nativo do QComboBox ao novo SLOT interno
        self.combo_box.currentTextChanged.connect(self._on_text_changed)
        
        # Layout (apenas para este exemplo simplificado)
        layout = QtWidgets.QHBoxLayout(self)
        layout.addWidget(self.combo_box)
        self.setLayout(layout)

        # Labels e outras inicializações que você possa ter omitido...

    @QtCore.Slot(list)
    def set_options(self, options: list):
        """Método para popular o ComboBox com opções."""
        self.combo_box.clear()
        self.combo_box.addItems(options)
        
    @QtCore.Slot(str)
    def _on_text_changed(self, value: str):
        """
        Slot que é chamado quando o texto do ComboBox muda.
        Responsável por formatar e emitir o comando de negócios.
        """
        if not value:
            return

        # A ComboBox AGORA é responsável por criar o comando
        command = {
            "command": f"set_{self.key}", # Ex: "set_soundcard"
            "value": value
        }
        
        # Emite o sinal customizado com o comando formatado
        self.command_to_send.emit(command) 

        