import cv2

CAMERA_INDEX = 0
drawing = False
ix, iy = -1, -1
frame_atual = None
retangulos = []

def mouse_callback(event, x, y, flags, param):
    global ix, iy, drawing, frame_atual, retangulos

    if event == cv2.EVENT_LBUTTONDOWN:
        drawing = True
        ix, iy = x, y

    elif event == cv2.EVENT_MOUSEMOVE and drawing:
        temp = frame_atual.copy()
        cv2.rectangle(temp, (ix, iy), (x, y), (0, 255, 0), 2)
        cv2.imshow("Selecionar areas", temp)

    elif event == cv2.EVENT_LBUTTONUP:
        drawing = False

        x1, y1 = min(ix, x), min(iy, y)
        x2, y2 = max(ix, x), max(iy, y)

        w = x2 - x1
        h = y2 - y1

        retangulos.append((x1, y1, w, h))

        print(f'"rect": ({x1}, {y1}, {w}, {h})')

cap = cv2.VideoCapture(CAMERA_INDEX)

cv2.namedWindow("Selecionar areas")
cv2.setMouseCallback("Selecionar areas", mouse_callback)

print("Clique e arraste para selecionar uma area.")
print("Aperte ESPACO para congelar/atualizar imagem.")
print("Aperte C para limpar.")
print("Aperte Q para sair.")

congelado = False

while True:
    if not congelado:
        ret, frame = cap.read()
        if not ret:
            print("Erro ao abrir webcam")
            break
        frame_atual = frame.copy()

    tela = frame_atual.copy()

    for i, (x, y, w, h) in enumerate(retangulos, start=1):
        cv2.rectangle(tela, (x, y), (x+w, y+h), (0, 255, 0), 2)
        cv2.putText(
            tela,
            f"{i}: ({x},{y},{w},{h})",
            (x, y - 8),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.45,
            (0, 255, 0),
            1
        )

    cv2.imshow("Selecionar areas", tela)

    key = cv2.waitKey(1) & 0xFF

    if key == ord("q"):
        break

    elif key == ord("c"):
        retangulos.clear()
        print("Areas limpas.")

    elif key == 32:  # ESPACO
        congelado = not congelado
        if congelado:
            print("Imagem congelada. Selecione as areas.")
        else:
            print("Imagem ao vivo.")

cap.release()
cv2.destroyAllWindows()

print("\nAreas selecionadas:")
for i, rect in enumerate(retangulos, start=1):
    print(f"{i}: {rect}")