from flask import Flask, request, jsonify, url_for, send_file
import sys, signal, os, eyed3, time
from demucs.apply import apply_model
from demucs.pretrained import get_model
from demucs.audio import AudioFile, save_audio
from multiprocessing import Process, Queue
import pickle, socket, selectors
import threading, queue


# no progress temos de meter a musica que queremos criar ou seja damos as tracks e ele cria a musica

app = Flask(__name__)
# Cria uma fila de tarefas

task_queue = queue.Queue()
response_queue = queue.Queue() 

Music = {}

socket_server = None

# Configurações do servidor de socket
HOST = '0.0.0.0'  # Endereço IP do servidor
PORT = 5000  # Porta do servidor


class Socket_Server:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.workers_socket = []
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen()
        self.workers = []

    def accept_connection(self):
        while True:
            # aceita a conexão dos workers
            print("Waiting for connection on "+ str(HOST)+":"+str(PORT))
            conn, addr = self.server_socket.accept()
            print("Connection from", conn, addr)
            self.workers.append(conn)
            print("Connection from worker accepted")

    def send_message_to_workers(self, message):
        pickleData = pickle.dumps(message)
         # envia a mensagem para um worker
        results = []
        for worker in self.workers:
            try:
                 # Verifica se o socket do worker ainda está conectado
                if worker.fileno() == -1:
                    print("Worker disconnected, skipping...")
                    continue
                # envia a manesagem para o worker mas manda 2 bytes iniciais com o tamanho da mensagem
                worker.sendall(len(pickleData).to_bytes(4, 'big')+pickleData)
                results.append(worker)
                break
            except Exception as e:
                print(f"Error sending message to worker: {e}")
                results.append(None)
                
        return results
       
    def receive_result_from_workers(self):
        results = []
        for worker in self.workers:
            try:
     
                # Recebe os 4 bytes iniciais com o tamanho da mensagem
                size_bytes = worker.recv(4)
                if not size_bytes:
                    results.append(None)
                    continue

                message_size = int.from_bytes(size_bytes, 'big')

                # Inicializa um buffer vazio para armazenar os dados da mensagem
                message_buffer = bytearray()

                # Continua recebendo os dados até que o tamanho total seja alcançado
                while len(message_buffer) < message_size:
                    remaining_bytes = message_size - len(message_buffer)
                    data = worker.recv(remaining_bytes)
                    if not data:
                        results.append(None)
                        break
                    message_buffer.extend(data)
                
                if len(message_buffer) == message_size:
                    # Transforma o buffer em bytes utilizando o utf-8
                    message_buffer = bytes(message_buffer)
                    # Decodifica a mensagem utilizando o pickle
                    data = pickle.loads(message_buffer)
                    results.append(data)
            except Exception as e:
                print(f"Error receiving result from worker: {e}")
                results.append(None)

        
        return results

    def close_server_socket(self):
        # fecha o socket do servidor, e retirar os workers da lista
        for worker in self.workers:
            worker.close()
        self.server_socket.close()




def metadata_analise(filename,music_id):
    instruments = []

    # Obtain the name of the music and the band using the eyed3 library
    audiofile = eyed3.load(filename)
    if audiofile.tag is None:
        return [], "", "", ""

    name_music = audiofile.tag.title if audiofile.tag.title is not None else ""
    band = audiofile.tag.artist if audiofile.tag.artist is not None else ""

    instruments=["drums","vocals","bass","other"]

    return instruments, name_music, band, music_id



music_id = 0

@app.route('/tracks/<track_name>')
def download_track(track_name):
    task_queue.put({'task': 'download', 'filename' : track_name})

    results = response_queue.get()
    response_queue.task_done()

    file_data = results['file_data']

    temp_filename = track_name
    with open(temp_filename, 'wb') as file:
        file.write(file_data)

    # Envia o arquivo de áudio como resposta para o cliente
    return send_file(temp_filename, as_attachment=True)



@app.route('/init', methods=['GET'])
def init():
    print("\nClient joined the server!\n")
    return jsonify({'msg': 'Server is running'}), 200


#inicializar  um objeto mutex
mutex = threading.Lock()

@app.route('/music', methods=['POST'])
def submit():
    global music_id
    # Salva o arquivo de áudio no servidor
    file = request.files['file']
    if file is None:
        return jsonify({'error': 'No file provided'}), 405
    
    #bloquear mutex antes de visualizar o music_id
    mutex.acquire()
    #guardar a musica no servidor
    try:
        music_id += 1
        filename = 'music_'+str(music_id)+'.mp3'

    finally:
        #libertar mutex após visualização  do music_id
        mutex.release()
        
    print( "File created with name: "+ filename)
    file.save(filename)
    
    print(f"Music ID created: {music_id}")
   
    instruments, name_music, band, music_id = metadata_analise(filename, music_id)

    # Cria um dicionário com os dados da música
    Music[music_id] = {'music_id': music_id,'filename': filename, 'name': name_music, 'band': band, 'tracks': []}

    #   Cria a resposta
    response={'music_id': music_id, 'name': name_music, 'band': band, 'tracks': []}

    mutex.acquire()  #bloquear mutex antes de visualizar o track_id
    
    try:
        for i, instrument in enumerate(instruments):
            track = {
                'name': instrument,
                'track_id': i + 1    #cuidado concorrencia aqui
            }
            response['tracks'].append(track)
            Music[music_id]['tracks'].append(track)
    finally:
         #libertar mutex após visualização  do track_id
        mutex.release()

    print("Data sended to Client \n")

    return jsonify(response), 200


@app.route('/music/<music_id>', methods=['POST'])
def process_music(music_id):
    music_id=int(music_id)
    tracks_id=[]
    if music_id not in Music:
        return jsonify({'error': 'Music not found'}), 404
    
    # Obtém os instrumentos enviados na solicitação
    instrumentos_id = request.json.get('instruments', [])
    indx=0
    tracks_names = []
    for ids in instrumentos_id:
        for track in Music[music_id]['tracks']:
            if ids == track['track_id']:
                indx += 1
                tracks_id.append(track['track_id'])
                tracks_names.append(track['name'])


    if indx != len(tracks_names):
        return jsonify({'error': 'Track not found'}), 405

    #print da track id, a dizer intsrumento
    print(f"Tracks for processing: {tracks_names}")
    
    # pegar na musica e envia la para o worker
    audio_data = open('music_' + str(music_id) + '.mp3', 'rb').read()

   # Atualiza o dicionário Music[music_id] com os nomes das tracks selecionadas
    Music[music_id]['selected_tracks'] = tracks_names
    
    task_queue.put({
        'task': 'process',
        'music_id': music_id,
        'track_id': tracks_id,
        'track_name' : tracks_names,
        'filename': Music[music_id]['filename'],
        'audio_data': audio_data
    })

    # receber a resposta do worker
    results = response_queue.get()
    response_queue.task_done()

    # Cria a resposta
    response = {
        'Sucesso' : results['task']}
    print("Data sended to Client \n")
    return jsonify(response), 200

@app.route('/music/<music_id>', methods=['GET'])
def get_music(music_id):
    music_id=int(music_id)
    tracks_id=[]
    if music_id not in Music:
        return jsonify({'error': 'Music not found'}), 404

    selected_tracks = Music[music_id]['selected_tracks']

    for track in Music[music_id]['tracks']:
        if track['name'] in selected_tracks:
            tracks_id.append(track['track_id'])
        
    
    print("Asking for progress")
    
    task_queue.put({
        'task': 'progress',
        'music_id': music_id,
        'track_id': tracks_id,
        'selected_tracks': selected_tracks
    })

    results = response_queue.get()
    response_queue.task_done()

    if results['progress'] == 100:
        response = {
            'progress': 100,
            'instruments': results['instruments'],
            'final': results['final']
        }
    else: 
        response = {
            'progress': results['progress'],
            'instruments': "",
            'final': ""
        }
    print("Progress sended for user")
    return jsonify(response), 200


@app.route('/music', methods=['GET'])
def get_all():
    musicas = []
    for music_id in Music:
        musicas.append(Music[music_id])

    return jsonify(musicas), 200


@app.route('/jobs', methods=['GET'])
def get_all_works(): #acabar
    all_jobs = []
    print("Getting all jobs")
    task_queue.put({'task': 'jobs'})

    results = response_queue.get()
    response_queue.task_done()

    # guarda os jobs_id na lista
    for job_id in results['jobs']:
        all_jobs.append(job_id)
    print("Data sent to client")
    return jsonify(all_jobs), 200

@app.route('/jobs/<job_id>', methods=['GET']) #falta este
def get_job(job_id):
    job_id = int(job_id)

    print("Getting all jobs")
    task_queue.put({'task': 'jobs'})

    results = response_queue.get()
    response_queue.task_done()

    if job_id not in results['jobs']:
        return jsonify({'error': 'Job not found'}), 404

    # cria uma lista com a informação do job_id
    job_info = [job for job in results['jobs'].values() if job['job_id'] == job_id]

    return jsonify(job_info), 200

@app.route('/reset', methods=['POST'])
def reset():
    # Reset the workers
    task_queue.put({'task': 'reset'})
    #resest info server
    Music.clear()

    return jsonify({'msg': 'Reset workers'}), 200


def shutdown_server(signal, frame):
    print("\nShutting down server...")
    # Envia a mensagem de shutdown para os workers
    task_queue.put({'task': 'shutdown'})
    # Fecha o socket do servidor
    socket_server.close_server_socket()
    # Fecha a aplicação Flask e depois desliga o script
    os._exit(0)

def worker_thread():
    while True:
        task = task_queue.get()

        socket_server.send_message_to_workers(task)

        results = socket_server.receive_result_from_workers()

        for result in results:
            if result is not None:
                # Processar o resultado recebido do worker
                print(f"Received result from worker: {result}")
                response_queue.put(result)

        task_queue.task_done()
        

def run_socket_server():
    global socket_server
    socket_server = Socket_Server(HOST, PORT)
    socket_server.accept_connection()

if __name__ == '__main__':

    signal.signal(signal.SIGINT, shutdown_server)

    # Start the socket server in a separate thread
    socket_thread = threading.Thread(target=run_socket_server)
    socket_thread.start()

    # Start the worker thread to process tasks from the queue
    worker_thread = threading.Thread(target=worker_thread)
    worker_thread.start()

    # Start the Flask application
    app.run(host='0.0.0.0', port=8080)

    # Wait for the threads to complete
    socket_thread.join()
    worker_thread.join()

    
