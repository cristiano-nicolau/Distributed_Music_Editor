import requests
import json,os,signal


def init():
    url = 'http://192.168.0.9:8080/init'
    response = requests.get(url)
    if response.status_code == 200:
        code = 200
        msg = "Successful operation"
        data = response.json()
    print(f"\nStatus: {code} - {msg}")
    print(data, '\n')


def submit_music(file_path):
    url = 'http://192.168.0.9:8080/music'
    files = {'file': open(file_path, 'rb')}
    response = requests.post(url, files=files)
    if response.status_code == 200:
        code = 200
        msg = "Successful operation"
        data = response.json()
    else:
        code = response.status_code
        msg = "Invalid input"
        data = response.json()


    print(f"\nStatus: {code} - {msg}\n")
    print(data,"\n")


def process_music(music_id, lista_instrumentos):
    url = f'http://192.168.0.9:8080/music/{music_id}'
    data = {'instruments': lista_instrumentos}
    response = requests.post(url, json=data)
    
    if response.status_code == 200:
        code = 200
        msg = "Successful operation"
        data = response.json()
    if response.status_code == 405:
        code = 405
        msg = "Track not found"
        data = response.json()
    elif response.status_code == 404:
        code = 404
        msg = "Music not found"
        data = response.json()
    
    print(f"\nStatus: {code} - {msg}\n")


def get_all_music():
    url = f'http://192.168.0.9:8080/music'
    response = requests.get(url)
    if response.status_code==200:
        code=200
        data = response.json()
        msg = "Successful operation"

    print(f"\nStatus: {code} - {msg}\n")
    print(data,"\n")

def get_music(music_id):
    url = f'http://192.168.0.9:8080/music/{music_id}'
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        code = 200
        msg = "Successful operation"
    elif response.status_code == 404:
        data = response.json()
        code = 404
        msg = "Music not found"
    print(f"\nStatus: {code} - {msg}\n")
    print(data,"\n")

def get_all_works():
    url = f'http://192.168.0.9:8080/jobs'
    response = requests.get(url)
    if response.status_code==200:
        code=200
        data = response.json()
        msg = "Successful operation"
    elif response.status_code==404:
        code=404
        data = response.json()
        msg = "Invalid input"

    print(f"\nStatus: {code} - {msg}\n")
    if code == 200:
        print(data,"\n")
    
def get_work(work_id):
    url = f'http://192.168.0.9:8080/jobs/{work_id}'
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        code = 200
        msg = "Successful operation"
    elif response.status_code == 404:
        data = response.json()
        code = 404
        msg = "Work not found"
    print(f"\nStatus: {code} - {msg}\n")
    print(data,"\n")

def restart():
    url = 'http://192.168.0.9:8080/reset'
    response = requests.post(url)
    if response.status_code==200:
        code=200
        data = response.json()
        msg = "Successful operation"
    print(f"\nStatus: {code} - {msg}\n")




def main():
    init()

    while True:
        print('*******************************************')
        print(" Music Methods")
        print(" M1 - submeter uma musica")
        print(" M2 - obter detalhes de uma musica")
        print(" M3 - listar todas as músicas submetidas")
        print(" M4 - processar uma música\n")
        print(" System Methods")
        print(" S1 - listar todos os trabalhos")
        print(" S2 - obter detalhes de um trabalho")
        print(" S3 - reiniciar o sistema\n")
        print(" Exit")
        print(" Q - sair")
        print('*******************************************')
        escolha = input("\nDigite sua escolha: ").upper()
        print('\n')
        if escolha == "M1":
            file_path = input("Insira o arquivo (com .mp3): ")
            if os.path.isfile(file_path):
                submit_music(file_path)
            else:
                print("Insira um arquivo válido\n")

        elif escolha == "M2":
            music_id = input("Digite o id da musica: ")
            get_music(music_id)

        elif escolha == "M3":
            get_all_music()

        elif escolha == "M4":
            music_id = input("Digite o ID da música: ")
            if not music_id:
                print("Erro: insira ID.")
                continue
            listaTracksId = []
            print("Insira os instrumentos que deseja processar ['drums = 1','vocals = 2','bass = 3','other = 4'](pressione Enter para enviar):")

            while True:
                inputInstrumento = input("Digite o id do instrumento: ")

                if inputInstrumento.strip() == "":
                    break

                if inputInstrumento  in ["1", "2", "3", "4"]:
                    listaTracksId.append(int(inputInstrumento))
                else:
                    print("Erro: ID de música inválido.")
                    continue


            # Print do music id e dos instrumentos selecionados
            print(f"Music ID: {music_id}")
            print(f"Instrumentos selecionados: {listaTracksId}")

            process_music(music_id, listaTracksId)

        elif escolha == "S1":
            get_all_works() 
            
        elif escolha == "S2":
            work_id = input("Digite o id do trabalho: ")
            get_work(work_id)

        elif escolha == "S3":
            restart() 
            
        elif escolha == "Q":
            print("Saindo...")
            break
        else:
            print("Selecione um método válido\n")


if __name__ == '__main__':
    main()