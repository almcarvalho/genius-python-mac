import cv2
import numpy as np
import time
import requests

CAMERA_INDEX = 0
BASE_URL = "http://10.0.0.23:3000"

cap = cv2.VideoCapture(CAMERA_INDEX)

CORES = {
    1: "verde",
    2: "vermelho",
    3: "amarelo",
    4: "azul"
}

AREAS = {
    "VERDE": {"rect": (152, 174, 42, 34), "botao": 1},
    "VERMELHO": {"rect": (299, 147, 30, 32), "botao": 2},
    "AMARELO": {"rect": (171, 303, 38, 31), "botao": 3},
    "AZUL": {"rect": (290, 283, 31, 29), "botao": 4}
}

TEMPO_CALIBRACAO = 4.0

LIMIAR_DIF_BRILHO = 30
LIMIAR_MELHOR_DIFERENCA = 12
FRAMES_CONFIRMAR_COR = 2

TEMPO_SEM_LUZ_PARA_RESPONDER = 1.80
TEMPO_ENTRE_BOTOES = 0.35
TEMPO_RETRY_AGUARDE = 0.50
TEMPO_OCIOSO_RECUPERAR = 5.0
TEMPO_OCIOSO_REINICIAR = 15.0

brilho_base = {nome: None for nome in AREAS}

sequencia_lida = []
nivel_atual = 1
recorde = 0

respondendo = False
pode_ler_nova_cor = True
ultimo_estado = "NENHUMA"

ultima_cor_detectada = None
contador_cor_detectada = 0

ultimo_evento = time.time()
ultimo_frame_com_luz = time.time()


def sequencia_para_texto(seq):
    return [CORES.get(n, "?") for n in seq]


def nome_para_botao(nome):
    return AREAS[nome]["botao"]


def pegar_estado():
    try:
        response = requests.get(f"{BASE_URL}/estado", timeout=3)
        return response.json()
    except Exception as e:
        print("Erro ao pegar estado:", e)
        return {}


def atualizar_nivel_pela_api():
    global nivel_atual, recorde

    estado = pegar_estado()

    if isinstance(estado.get("nivel"), int):
        nivel_atual = estado["nivel"]

    if isinstance(estado.get("recorde"), int):
        recorde = estado["recorde"]

    return estado


def chamar_api_cor(numero):
    url = f"{BASE_URL}/cor/{numero}"

    try:
        response = requests.get(url, timeout=3)

        try:
            data = response.json()
        except Exception:
            data = {}

        print(
            f"API -> {numero} ({CORES[numero]}) | "
            f"status={response.status_code} | "
            f"nivel={data.get('nivel')} | "
            f"recorde={data.get('recorde')} | "
            f"msg={data.get('mensagem')}"
        )

        return data

    except Exception as e:
        print("ERRO API:", e)
        return {}


def enviar_cor_com_retry(botao):
    while True:
        retorno = chamar_api_cor(botao)
        msg = str(retorno.get("mensagem", "")).lower()

        if "aguarde" in msg:
            print("API ainda está mostrando a sequência. Tentando novamente...")
            time.sleep(TEMPO_RETRY_AGUARDE)
            continue

        return retorno


def recalibrar_brilho():
    global brilho_base

    brilho_base = {nome: None for nome in AREAS}

    print("Recalibrando brilho... deixe todos apagados")

    inicio = time.time()

    while time.time() - inicio < TEMPO_CALIBRACAO:
        ret, frame = cap.read()

        if not ret:
            print("Erro webcam na calibração")
            return

        for nome, dados in AREAS.items():
            x, y, w, h = dados["rect"]
            roi = frame[y:y+h, x:x+w]

            gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
            brilho = np.mean(gray)

            if brilho_base[nome] is None:
                brilho_base[nome] = brilho
            else:
                brilho_base[nome] = brilho_base[nome] * 0.90 + brilho * 0.10

            cv2.rectangle(frame, (x, y), (x+w, y+h), (255, 255, 0), 2)
            cv2.putText(
                frame,
                "CALIBRANDO",
                (x, y - 8),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.42,
                (255, 255, 0),
                1
            )

        cv2.imshow("Genius Bot", frame)

        if cv2.waitKey(1) & 0xFF == ord("q"):
            cap.release()
            cv2.destroyAllWindows()
            exit()

    print("Brilho base:")
    for nome, valor in brilho_base.items():
        print(f"{nome}: {valor:.1f}")


def detectar_brilho_roi(roi, nome):
    gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
    brilho = np.mean(gray)

    if brilho_base[nome] is None:
        brilho_base[nome] = brilho

    diff = brilho - brilho_base[nome]
    return brilho, diff


def detectar_quadrado_aceso(frame):
    leituras = []

    for nome, dados in AREAS.items():
        x, y, w, h = dados["rect"]
        roi = frame[y:y+h, x:x+w]

        brilho, diff = detectar_brilho_roi(roi, nome)

        leituras.append({
            "nome": nome,
            "botao": dados["botao"],
            "rect": dados["rect"],
            "brilho": brilho,
            "diff": diff
        })

    leituras.sort(key=lambda item: item["diff"], reverse=True)

    melhor = leituras[0]
    segundo = leituras[1]

    if melhor["diff"] < LIMIAR_DIF_BRILHO:
        return "NENHUMA", leituras

    if melhor["diff"] - segundo["diff"] < LIMIAR_MELHOR_DIFERENCA:
        return "INDEFINIDO", leituras

    return melhor["nome"], leituras


def confirmar_estado(estado):
    global ultima_cor_detectada, contador_cor_detectada

    if estado in ["NENHUMA", "INDEFINIDO"]:
        ultima_cor_detectada = estado
        contador_cor_detectada = 0
        return estado

    if estado == ultima_cor_detectada:
        contador_cor_detectada += 1
    else:
        ultima_cor_detectada = estado
        contador_cor_detectada = 1

    if contador_cor_detectada >= FRAMES_CONFIRMAR_COR:
        return estado

    return "NENHUMA"


def tentar_recuperar_pela_api():
    estado = pegar_estado()
    seq = estado.get("sequencia", [])

    if isinstance(seq, list) and len(seq) >= nivel_atual:
        seq = seq[:nivel_atual]

        print("\nRECUPERANDO PELA API")
        print("Sequência câmera:", sequencia_lida)
        print("Sequência API:", seq)
        print("Cores API:", sequencia_para_texto(seq))

        return seq

    return None


def responder_sequencia(seq):
    global respondendo
    global sequencia_lida
    global nivel_atual
    global recorde
    global pode_ler_nova_cor
    global ultimo_estado
    global ultimo_evento
    global ultimo_frame_com_luz
    global ultima_cor_detectada
    global contador_cor_detectada

    respondendo = True

    print("\n==============================")
    print("RESPONDENDO")
    print("NÍVEL:", nivel_atual)
    print("SEQUÊNCIA:", seq)
    print("CORES:", sequencia_para_texto(seq))
    print("==============================")

    ultimo_retorno = {}

    for botao in seq:
        ultimo_retorno = enviar_cor_com_retry(botao)

        msg = str(ultimo_retorno.get("mensagem", "")).lower()

        if "errou" in msg:
            print("Parando envio porque a API informou erro.")
            break

        time.sleep(TEMPO_ENTRE_BOTOES)

    if isinstance(ultimo_retorno.get("nivel"), int):
        nivel_atual = ultimo_retorno["nivel"]

    if isinstance(ultimo_retorno.get("recorde"), int):
        recorde = ultimo_retorno["recorde"]

    sequencia_lida = []
    pode_ler_nova_cor = True
    ultimo_estado = "NENHUMA"
    ultima_cor_detectada = None
    contador_cor_detectada = 0

    ultimo_evento = time.time()
    ultimo_frame_com_luz = time.time()

    print("RESPOSTA FINALIZADA")
    print("PRÓXIMO NÍVEL:", nivel_atual)
    print("RECORDE:", recorde)
    print("==============================\n")

    time.sleep(0.8)
    respondendo = False


print("Genius Bot iniciado")
print("Modo: câmera lê sequência + API responde")
print("Q = sair | R = recalibrar")

recalibrar_brilho()
time.sleep(0.5)

atualizar_nivel_pela_api()

print("Nível inicial:", nivel_atual)
print("\nMONITORANDO...\n")

while True:
    ret, frame = cap.read()

    if not ret:
        print("Erro webcam")
        break

    agora = time.time()

    estado_bruto, leituras = detectar_quadrado_aceso(frame)
    estado_atual = confirmar_estado(estado_bruto)

    if estado_atual not in ["NENHUMA", "INDEFINIDO"]:
        ultimo_frame_com_luz = agora

    if not respondendo:
        tempo_sem_luz = agora - ultimo_frame_com_luz
        tempo_ocioso = agora - ultimo_evento

        if estado_atual == "NENHUMA":
            pode_ler_nova_cor = True
            ultimo_estado = "NENHUMA"

            if (
                len(sequencia_lida) >= nivel_atual
                and tempo_sem_luz >= TEMPO_SEM_LUZ_PARA_RESPONDER
            ):
                responder_sequencia(sequencia_lida.copy())

            elif (
                len(sequencia_lida) > 0
                and len(sequencia_lida) < nivel_atual
                and tempo_ocioso >= TEMPO_OCIOSO_RECUPERAR
            ):
                seq_api = tentar_recuperar_pela_api()

                if seq_api is not None:
                    responder_sequencia(seq_api)

            elif tempo_ocioso >= TEMPO_OCIOSO_REINICIAR:
                seq_api = tentar_recuperar_pela_api()

                if seq_api is not None:
                    responder_sequencia(seq_api)
                else:
                    print("Ocioso, mas sem sequência recuperável. Aguardando...")

                    ultimo_evento = time.time()

        elif estado_atual == "INDEFINIDO":
            pass

        elif pode_ler_nova_cor and estado_atual != ultimo_estado:
            botao = nome_para_botao(estado_atual)

            sequencia_lida.append(botao)
            ultimo_evento = agora

            print(
                f"NÍVEL {nivel_atual} | "
                f"COR LIDA: {estado_atual} ({botao}) | "
                f"SEQUÊNCIA LIDA: {sequencia_lida} | "
                f"CORES: {sequencia_para_texto(sequencia_lida)}"
            )

            pode_ler_nova_cor = False
            ultimo_estado = estado_atual

    for item in leituras:
        x, y, w, h = item["rect"]

        ativo = item["nome"] == estado_atual

        if estado_bruto == "INDEFINIDO":
            cor_borda = (0, 255, 255)
        else:
            cor_borda = (0, 255, 0) if ativo else (0, 0, 255)

        cv2.rectangle(frame, (x, y), (x+w, y+h), cor_borda, 2)

        cv2.putText(
            frame,
            f"{item['nome']} D:{item['diff']:.1f}",
            (x, y - 8),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.42,
            cor_borda,
            1
        )

    cv2.putText(
        frame,
        f"Nivel: {nivel_atual}",
        (20, 30),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.8,
        (255, 255, 255),
        2
    )

    cv2.putText(
        frame,
        f"Lida: {len(sequencia_lida)}/{nivel_atual}",
        (20, 60),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.8,
        (255, 255, 255),
        2
    )

    cv2.putText(
        frame,
        f"Sem luz: {agora - ultimo_frame_com_luz:.1f}s",
        (20, 90),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.8,
        (255, 255, 255),
        2
    )

    cv2.imshow("Genius Bot", frame)

    key = cv2.waitKey(1) & 0xFF

    if key == ord("q"):
        break

    elif key == ord("r"):
        sequencia_lida = []
        ultimo_estado = "NENHUMA"
        pode_ler_nova_cor = True
        ultimo_evento = time.time()
        ultimo_frame_com_luz = time.time()
        ultima_cor_detectada = None
        contador_cor_detectada = 0
        recalibrar_brilho()

cap.release()
cv2.destroyAllWindows()