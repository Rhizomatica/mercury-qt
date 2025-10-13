from PySide6 import QtCore, QtWidgets, QtGui
from modules.radio.view.json_detail_view import JsonDetailView
import modules.connection.udp.client as Client_UDP

class MainWidget(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Mercury Qt - Like")
        self.setGeometry(100, 100, 900, 600)
        
        # Dados atuais
        self.current_status = {}
        self.soundcards = []
        self.selected_soundcard = ""
        self.radios = []
        self.selected_radio = ""

        # Configurar cliente UDP
        self.client = Client_UDP.ClientUDP()
        self.client.json_received.connect(self.handle_json_data)
        self.client.start_udp_client()

        self.setup_ui()

    def setup_ui(self):
        main_layout = QtWidgets.QHBoxLayout(self)
    
        # Coluna esquerda - Status principal
        left_column = QtWidgets.QVBoxLayout()
        
        # Grupo de controle
        control_group = QtWidgets.QGroupBox("Controle")
        control_layout = QtWidgets.QVBoxLayout()
        self.btn_settings = QtWidgets.QPushButton("CONFIGURAÇÕES")
        control_layout.addWidget(self.btn_settings)
        control_group.setLayout(control_layout)
        left_column.addWidget(control_group)
        
        # Grupo de callsigns
        callsign_group = QtWidgets.QGroupBox("Callsigns")
        callsign_layout = QtWidgets.QFormLayout()
        
        self.lbl_my_callsign = QtWidgets.QLabel("--")
        self.lbl_dest_callsign = QtWidgets.QLabel("--")
        
        callsign_layout.addRow("Meu Callsign:", self.lbl_my_callsign)
        callsign_layout.addRow("Callsign Destino:", self.lbl_dest_callsign)
        
        callsign_group.setLayout(callsign_layout)
        left_column.addWidget(callsign_group)
        
        
        # Grupo de status da conexão
        status_group = QtWidgets.QGroupBox("Status da Conexão")
        status_layout = QtWidgets.QGridLayout()
        
        # Labels de status
        self.lbl_bitrate = QtWidgets.QLabel("Bitrate: --")
        self.lbl_snr = QtWidgets.QLabel("SNR: -- dB")
        self.lbl_sync = QtWidgets.QLabel("Sincronismo: NÃO")
        self.lbl_direction = QtWidgets.QLabel("Direção: --")
        self.lbl_connected = QtWidgets.QLabel("TCP Conectado: NÃO")
        
        status_layout.addWidget(QtWidgets.QLabel("Taxa:"), 0, 0)
        status_layout.addWidget(self.lbl_bitrate, 0, 1)
        status_layout.addWidget(QtWidgets.QLabel("Sinal:"), 1, 0)
        status_layout.addWidget(self.lbl_snr, 1, 1)
        status_layout.addWidget(QtWidgets.QLabel("Sync:"), 2, 0)
        status_layout.addWidget(self.lbl_sync, 2, 1)
        status_layout.addWidget(QtWidgets.QLabel("Modo:"), 3, 0)
        status_layout.addWidget(self.lbl_direction, 3, 1)
        status_layout.addWidget(QtWidgets.QLabel("TCP:"), 4, 0)
        status_layout.addWidget(self.lbl_connected, 4, 1)
        
        status_group.setLayout(status_layout)
        left_column.addWidget(status_group)
        
 
        
        # Grupo de contadores
        counter_group = QtWidgets.QGroupBox("Contadores")
        counter_layout = QtWidgets.QFormLayout()
        
        self.lbl_tx_bytes = QtWidgets.QLabel("0")
        self.lbl_rx_bytes = QtWidgets.QLabel("0")
        
        counter_layout.addRow("Bytes Transmitidos:", self.lbl_tx_bytes)
        counter_layout.addRow("Bytes Recebidos:", self.lbl_rx_bytes)
        
        counter_group.setLayout(counter_layout)
        left_column.addWidget(counter_group)
        
        # Coluna direita - Controles e informações
        right_column = QtWidgets.QVBoxLayout()
        
        # Grupo de dispositivos
        devices_group = QtWidgets.QGroupBox("Dispositivos")
        devices_layout = QtWidgets.QVBoxLayout()
        
        # Soundcard
        soundcard_group = QtWidgets.QGroupBox("Soundcard")
        soundcard_layout = QtWidgets.QVBoxLayout()
        self.combo_soundcard = QtWidgets.QComboBox()
        soundcard_layout.addWidget(self.combo_soundcard)
        soundcard_group.setLayout(soundcard_layout)
        
        # Rádio
        radio_group = QtWidgets.QGroupBox("Rádio")
        radio_layout = QtWidgets.QVBoxLayout()
        self.combo_radio = QtWidgets.QComboBox()
        radio_layout.addWidget(self.combo_radio)
        radio_group.setLayout(radio_layout)
        
        devices_layout.addWidget(soundcard_group)
        devices_layout.addWidget(radio_group)
        devices_group.setLayout(devices_layout)
        right_column.addWidget(devices_group)
        
 
        
        # # Área de log (opcional)
        # log_group = QtWidgets.QGroupBox("Log")
        # log_layout = QtWidgets.QVBoxLayout()
        # self.text_log = QtWidgets.QTextEdit()
        # self.text_log.setMaximumHeight(150)
        # self.text_log.setReadOnly(True)
        # log_layout.addWidget(self.text_log)
        # log_group.setLayout(log_layout)
        # right_column.addWidget(log_group)
        
        # Adicionar colunas ao layout principal
        main_layout.addLayout(left_column, 2)
        main_layout.addLayout(right_column, 1)
        
        # Configurar estilos
        #self.setup_styles()

    #def setup_styles(self):
        # Estilos 
        # self.setStyleSheet("""
        #     QGroupBox {
        #         font-weight: bold;
        #         border: 1px solid gray;
        #         border-radius: 5px;
        #         margin-top: 1ex;
        #         padding-top: 10px;
        #     }
            
        #     QGroupBox::title {
        #         subcontrol-origin: margin;
        #         left: 10px;
        #         padding: 0 5px 0 5px;
        #     }
            
        #     QLabel {
        #         font-family: "Courier New", monospace;
        #     }
            
        #     QPushButton {
        #         font-weight: bold;
        #         padding: 5px;
        #         min-height: 20px;
        #     }
            
        #     QPushButton:hover {
        #         background-color: #e0e0e0;
        #     }
            
        #     QTextEdit {
        #         font-family: "Courier New", monospace;
        #         font-size: 10px;
        #     }
        # """)
    def load_styles(self):
        """Carrega os estilos do arquivo QSS"""
        try:
            # Ajuste o caminho conforme a estrutura do seu projeto
            styles_path = os.path.join(os.path.dirname(__file__), "styles", "app.qss")
            
            with open(styles_path, "r", encoding="utf-8") as file:
                stylesheet = file.read()
                self.setStyleSheet(stylesheet)
                
        except FileNotFoundError:
            print(f"Arquivo de estilos não encontrado: {styles_path}")
        except Exception as e:
            print(f"Erro ao carregar estilos: {e}")
    @QtCore.Slot(dict)
    def handle_json_data(self, data: dict):
        """Processa os dados JSON recebidos"""
        msg_type = data.get("type", "")
        
        if msg_type == "status":
            self.handle_status_data(data)
        elif msg_type == "soundcard_list":
            self.handle_soundcard_data(data)
        elif msg_type == "radio_list":
            self.handle_radio_data(data)
        
        # # Adiciona ao log
        # self.add_to_log(f"Recebido: {msg_type}")

    def handle_status_data(self, data):
        """Atualiza os dados de status"""
        self.current_status = data
        
        # Atualizar interface
        self.lbl_bitrate.setText(f"{data.get('bitrate', '--')} bps")
        
        snr = data.get('snr', 0)
        self.lbl_snr.setText(f"{snr:.1f} dB")
        
        sync = data.get('sync', False)
        self.lbl_sync.setText("SIM" if sync else "NÃO")
        
        direction = data.get('direction', '')
        direction_text = "TRANSMITINDO" if direction == 'tx' else "RECEBENDO" if direction == 'rx' else "IDLE"
        self.lbl_direction.setText(direction_text)
        
        connected = data.get('client_tcp_connected', False)
        self.lbl_connected.setText("SIM" if connected else "NÃO")
        
        self.lbl_my_callsign.setText(data.get('user_callsign', '--'))
        self.lbl_dest_callsign.setText(data.get('dest_callsign', '--'))
        
        self.lbl_tx_bytes.setText(str(data.get('bytes_transmitted', 0)))
        self.lbl_rx_bytes.setText(str(data.get('bytes_received', 0)))
        
        # Mudar cores baseado no estado
        self.update_status_colors(direction, sync)

    def handle_soundcard_data(self, data):
        """Atualiza lista de soundcards"""
        self.soundcards = data.get('list', [])
        self.selected_soundcard = data.get('selected', '')
        
        self.combo_soundcard.clear()
        self.combo_soundcard.addItems(self.soundcards)
        
        # Selecionar o item atual
        if self.selected_soundcard in self.soundcards:
            index = self.soundcards.index(self.selected_soundcard)
            self.combo_soundcard.setCurrentIndex(index)

    def handle_radio_data(self, data):
        """Atualiza lista de rádios"""
        self.radios = data.get('list', [])
        self.selected_radio = data.get('selected', '')
        
        self.combo_radio.clear()
        self.combo_radio.addItems(self.radios)
        
        # Selecionar o item atual
        if self.selected_radio in self.radios:
            index = self.radios.index(self.selected_radio)
            self.combo_radio.setCurrentIndex(index)

    def update_status_colors(self, direction, sync):
        """Atualiza cores baseado no estado atual"""
        # Reset cores
        self.lbl_direction.setStyleSheet("")
        self.lbl_sync.setStyleSheet("")
        
        if direction == 'tx':
            self.lbl_direction.setStyleSheet("color: red; font-weight: bold;")
        elif direction == 'rx':
            self.lbl_direction.setStyleSheet("color: green; font-weight: bold;")
        
        if sync:
            self.lbl_sync.setStyleSheet("color: blue; font-weight: bold;")
    
    # def add_to_log(self, message):
    #     """Adiciona mensagem ao log"""
    #     timestamp = QtCore.QDateTime.currentDateTime().toString("hh:mm:ss")
    #     self.text_log.append(f"[{timestamp}] {message}")
        
    #     # Limitar o tamanho do log
    #     if self.text_log.document().lineCount() > 100:
    #         cursor = self.text_log.textCursor()
    #         cursor.movePosition(QtGui.QTextCursor.Start)
    #         cursor.select(QtGui.QTextCursor.BlockUnderCursor)
    #         cursor.removeSelectedText()

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    widget = MainWidget()
    widget.show()
    sys.exit(app.exec())