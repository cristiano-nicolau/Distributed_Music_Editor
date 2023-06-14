import os,time, sys
from demucs.apply import apply_model
from demucs.pretrained import get_model
from demucs.audio import AudioFile, save_audio
from multiprocessing import Process, Value, Manager
import socket
from pydub import AudioSegment
import pickle, signal
import argparse
import urllib.parse

import torch
torch.set_num_threads(1)

HOST = '192.168.0.9'
PORT = 5000

progress = Value('d', 0.0)
jobs = dict()
job_id = 0

def process_music(audio, track_name, music_id,jobs,start_time,job_id):
    global progress

    model = get_model(name='htdemucs')
    model.cpu()
    model.eval()

    # Load the audio file
    wav = AudioFile(audio).read(
        streams=0,
        samplerate=model.samplerate,
        channels=model.audio_channels
    )
    ref = wav.mean(0)
    wav = (wav - ref.mean()) / ref.std()

    # Apply the model
    sources = apply_model(model, wav[None], device='cpu', progress=True, num_workers=1)[0]
    sources = sources * ref.std() + ref.mean()

    # Store the model
    total_tracks = len(track_name)
    processed_tracks = 0

    for source, name in zip(sources, model.sources):
        for index,track in enumerate(track_name):
            if name == track:    
                stem = f'tracks/{name}_music_{music_id}.wav'
                save_audio(source, stem, samplerate=model.samplerate)
                print(f"Track {name} saved to {stem}")
                processed_tracks += 1
                progress.value = processed_tracks / total_tracks
                print(f"Progress: {progress.value * 100:.2f}%")
    
    end_time = time.time()
    processing_time = end_time - start_time
    jobs[job_id]['time'] = processing_time
    print(f"Worker created job {job_id}")

    return jobs


def progress_music(tracks,music_id,size):
    #loads tracks
    tracks = [AudioSegment.from_wav(track) for track in tracks]
    #merge tracks
    audio = tracks[0]
    for track in tracks[1:]:
        audio = audio.overlay(track, position=0)
    #export merged track
    audio.export(f'tracks/merged_music_{music_id}.wav', format='wav')

    size += os.path.getsize(f'tracks/merged_music_{music_id}.wav')

    base_url = 'http://127.0.0.1:8080/tracks/'
    #url da musica final
    url = urllib.parse.urljoin(base_url, f'merged_music_{music_id}.wav')

    return url,size



def worker(worker_id, host, port):
    global job_id
    print(f"Worker {worker_id} started")

    # Create a TCP socket
    worker_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    try:
        # Connect to the server
        worker_socket.connect((host, port))
        print(f"Worker {worker_id} connected to server at {host}:{port}")

        def send_progress_to_server(music_id, progress):
            progresso = progress.value * 100
            message = {
                'music_id': music_id,
                'progress': progresso
            }
            message = pickle.dumps(message)
            message_size = len(message).to_bytes(4, 'big')
            worker_socket.sendall(message_size + message)
            print(f"Worker {worker_id} sent progress update to server")


        while True:
            # Recebe os 4 bytes iniciais com o tamanho da mensagem
            size_bytes = worker_socket.recv(4)
            if not size_bytes:
                return None

            message_size = int.from_bytes(size_bytes, 'big')

            # Inicializa um buffer vazio para armazenar os dados da mensagem
            message_buffer = bytearray()

            # Continua recebendo os dados até que o tamanho total seja alcançado
            while len(message_buffer) < message_size:
                remaining_bytes = message_size - len(message_buffer)    
                data = worker_socket.recv(remaining_bytes)
                if not data:
                    return None
                message_buffer.extend(data)
            
            #tranforma o message buffer em bytes utilizando o utf 8
            message_buffer = bytes(message_buffer)
            # Decodifica a mensagem utilizando o pickle
            data = pickle.loads(message_buffer)

            task = data['task']
            print(f"Worker {worker_id} received task {task}")

            if task == "process":
                
                job_id += 1
                start_time = time.time()


                tracks_name = []
                music_id = data['music_id']
                filename = data['filename']
                tracks_id = data["track_id"]
                tracks_name = data["track_name"]
                audio_data = data['audio_data'] 
                print(tracks_name)
                
                #guardar o ficheiro audio
                with open(f'tracks/music_{music_id}.mp3', "wb") as f:
                    f.write(audio_data)
                audio_data = f'tracks/music_{music_id}.mp3' 
                
                message = { 'task': 'processing music'
                }
                message = pickle.dumps(message)
                message_size = len(message).to_bytes(4, 'big')
                worker_socket.sendall(message_size + message)
                print(f"Worker {worker_id} sent message to server")

                jobs[job_id]={'job_id' : job_id,'time': 0,'size':0,'music_id' : music_id, 'tracks_id' : tracks_id }

                #processar a musica em uma thread
                process = Process(target=process_music, args=(audio_data, tracks_name, music_id,jobs,start_time,job_id))
                process.start()
                print(f"Worker {worker_id} processed music {music_id}")
                


            if task == "shutdown":
                break

            if task == "progress":
                global progress
                size=0
                job_id += 1
                start_time = time.time()

                #se o progress nao for igual a 100% enviar progresso para o server
                if progress.value == 1:
                    tracks = []
                    music_id = data['music_id']
                    selected_tracks = data['selected_tracks']
                                
                    for instrumento in selected_tracks:
                        filename = f'{instrumento}_music_{music_id}.wav'
                        filepath = os.path.join('tracks', filename)
                        if os.path.exists(filepath):
                            tracks.append(filepath)
                            size += os.path.getsize(filepath)
                        print(tracks)


                    finalurl,size = progress_music(tracks,music_id,size)
                    
                    base_url = 'http://127.0.0.1:8080/tracks'
                    tracks_urls=[urllib.parse.urljoin(base_url, urllib.parse.quote(track)) for track in tracks]
                    
                    #criar um dicionario com o selected track e a url
                    tracks_urls_dict = []
                    for track, url in zip(selected_tracks, tracks_urls):
                        track_dict = {'track': track, 'url': url}
                        tracks_urls_dict.append(track_dict)
                    
                    message = {
                        'progress': 100,
                        'music_id': music_id,
                        'instruments': [tracks_urls_dict],
                        'final': finalurl
                    }
                    message = pickle.dumps(message)
                    message_size = len(message).to_bytes(4, 'big')
                    worker_socket.sendall(message_size + message)
                    print(f"Worker {worker_id} sent message to server")
            
                else:
                    music_id = data['music_id']
                    send_progress_to_server(music_id, progress)

                #set jobs
                end_time = time.time()
                processing_time = end_time - start_time
                jobs[job_id]={'job_id' : job_id,'time':processing_time,'size':size ,'music_id' : music_id, 'tracks_id' : [data['track_id']] }
                print(f"Worker {worker_id} created job {job_id}")


            if task == "jobs":
                message = {
                    'jobs': jobs
                }
                message = pickle.dumps(message)
                message_size = len(message).to_bytes(4, 'big')
                worker_socket.sendall(message_size + message)
                print(f"Worker {worker_id} sent message to server")

            if task == "reset":
                jobs.clear()
                tracks_directory = 'tracks'
                if not os.path.exists(tracks_directory):
                    os.makedirs(tracks_directory)
                for file in os.listdir(tracks_directory):
                    file_path = os.path.join(tracks_directory, file)
                    os.remove(file_path)
                print("All files removed from 'tracks' directory")
                print("Worker stopped")
                break

            if task == "download":
                filename = data['filename']

                # Verifica se o arquivo existe na pasta 'tracks'
                if os.path.exists(f'tracks/{filename}'):
                    # Lê o arquivo de áudio
                    with open(f'tracks/{filename}', 'rb') as f:
                        audio_data = f.read()

                    # Prepara a mensagem a ser enviada de volta para o servidor Flask
                    message = {
                        'filename': filename,
                        'file_data': audio_data
                    }

                    # Serializa a mensagem usando pickle
                    message_bytes = pickle.dumps(message)

                    # Obtém o tamanho da mensagem serializada
                    message_size = len(message_bytes).to_bytes(4, 'big')

                    # Envia o tamanho da mensagem seguido pelos dados da mensagem
                    worker_socket.sendall(message_size + message_bytes)
                    print(f"Worker {worker_id} sent message to server")
                else:
                    print(f"Worker {worker_id} could not find file {filename}")
                    continue

    finally:
        # Close the socket
        worker_socket.close()
        print(f"Worker {worker_id} exited")
        
def shutdown_server(signal, frame):
    print("\nShutting down worker...")
    sys.exit(0)



if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Worker script')
    parser.add_argument('worker_id', type=int, default=1, help='ID of the worker')
    args = parser.parse_args()

    signal.signal(signal.SIGINT, shutdown_server)

    worker(args.worker_id, HOST, PORT)
