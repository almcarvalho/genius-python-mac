import cv2
import numpy as np
import time

CAMERA_INDEX = 0

cap = cv2.VideoCapture(CAMERA_INDEX)

AREAS = {
    "VERDE": {
        "rect": (152, 174, 42, 34),
        "botao": 1
    },
    "VERMELHO": {
        "rect": (299, 147, 30, 32),
        "botao": 2
    },
    "AMARELO": {
        "rect": (171, 303, 38, 31),
        "botao": 3
    },
    "AZUL": {
        "rect": (290, 283, 31, 29),
        "botao": 4
    }
}

# brilho base de cada quadrado apagado
brilho_base = {
    nome: None
    for nome in AREAS
}

ULTIMO_ESTADO = "NENHUMA"

DEBOUNCE_TEMPO = 0.60
ultimo_tempo_evento = 0

# sensibilidade
LIMIAR_DIF_BRILHO = 30
LIMIAR_MELHOR_DIFERENCA = 12


def detectar_brilho_roi(roi, nome):
    gray = cv2.cvtColor(
        roi,
        cv2.COLOR_BGR2GRAY
    )

    brilho_medio = np.mean(gray)

    if brilho_base[nome] is None:
        brilho_base[nome] = brilho_medio

    diff = brilho_medio - brilho_base[nome]

    return brilho_medio, diff


def detectar_quadrado_aceso(frame):
    leituras = []

    for nome, dados in AREAS.items():
        x, y, w, h = dados["rect"]

        roi = frame[y:y+h, x:x+w]

        brilho, diff = detectar_brilho_roi(
            roi,
            nome
        )

        leituras.append({
            "nome": nome,
            "botao": dados["botao"],
            "rect": dados["rect"],
            "brilho": brilho,
            "diff": diff
        })

    leituras.sort(
        key=lambda item: item["diff"],
        reverse=True
    )

    melhor = leituras[0]
    segundo = leituras[1]

    if melhor["diff"] < LIMIAR_DIF_BRILHO:
        return "NENHUMA", leituras

    if (
        melhor["diff"] - segundo["diff"]
        < LIMIAR_MELHOR_DIFERENCA
    ):
        return "GAME OVER", leituras

    return melhor["nome"], leituras


print("Monitorando áreas por posição/brilho...")
print("Ignorando cor HSV.")
print("Posições fixas:")
print("- esquerda superior = VERDE")
print("- direita superior = VERMELHO")
print("- esquerda inferior = AMARELO")
print("- direita inferior = AZUL")
print("Q = sair | R = recalibrar")

while True:
    ret, frame = cap.read()

    if not ret:
        print("Erro webcam")
        break

    agora = time.time()

    estado_atual, leituras = detectar_quadrado_aceso(
        frame
    )

    mudou_estado = estado_atual != ULTIMO_ESTADO

    passou_debounce = (
        agora - ultimo_tempo_evento
        > DEBOUNCE_TEMPO
    )

    if mudou_estado and passou_debounce:
        if estado_atual == "GAME OVER":
            print("GAME OVER - mais de uma área acesa")

        elif estado_atual != "NENHUMA":
            print("COR PRESSIONADA:", estado_atual)

        ultimo_tempo_evento = agora
        ULTIMO_ESTADO = estado_atual

    for item in leituras:
        x, y, w, h = item["rect"]
        nome = item["nome"]

        ativo = estado_atual == nome

        if estado_atual == "GAME OVER":
            cor_borda = (0, 255, 255)
        else:
            cor_borda = (
                (0, 255, 0)
                if ativo
                else (0, 0, 255)
            )

        cv2.rectangle(
            frame,
            (x, y),
            (x+w, y+h),
            cor_borda,
            2
        )

        cv2.putText(
            frame,
            f"{nome} diff={item['diff']:.1f}",
            (x, y - 8),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.42,
            cor_borda,
            1
        )

    cv2.imshow(
        "Detector Genius",
        frame
    )

    key = cv2.waitKey(1) & 0xFF

    if key == ord("q"):
        break

    elif key == ord("r"):
        brilho_base = {
            nome: None
            for nome in AREAS
        }

        ULTIMO_ESTADO = "NENHUMA"
        ultimo_tempo_evento = 0

        print(
            "Recalibrando... "
            "deixe todos os quadrados apagados"
        )

cap.release()
cv2.destroyAllWindows()