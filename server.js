const express = require("express");
const app = express();

const PORT = 3000;

const cores = {
  1: "verde",
  2: "vermelho",
  3: "amarelo",
  4: "azul",
};

let sequencia = [];
let posicaoJogador = 0;
let nivel = 1;
let recorde = 0;
let mensagem = "Memorize a sequência";

let esperandoJogada = false;

let eventos = [];
let ultimoEventoId = 0;

function adicionarEvento(tipo, dados = {}) {
  ultimoEventoId++;

  eventos.push({
    id: ultimoEventoId,
    tipo,
    dados,
    momento: Date.now(),
  });

  if (eventos.length > 100) {
    eventos.shift();
  }
}

function novaCor() {
  let numero;

  do {
    numero = Math.floor(Math.random() * 4) + 1;
  } while (sequencia.length > 0 && numero === sequencia[sequencia.length - 1]);

  sequencia.push(numero);
}

function tempoDaSequencia() {
  return sequencia.length * 700 + 2200;
}

function liberarJogadaDepoisDaSequencia() {
  esperandoJogada = false;

  setTimeout(() => {
    esperandoJogada = true;
    mensagem = "Sua vez";
  }, tempoDaSequencia());
}

function iniciarJogo() {
  sequencia = [];
  posicaoJogador = 0;
  nivel = 1;
  novaCor();
  mensagem = "Memorize a sequência";
  esperandoJogada = false;

  liberarJogadaDepoisDaSequencia();
}

function jogar(cor, origem = "local") {
  const numero = Number(cor);

  if (!cores[numero]) {
    return {
      erro: true,
      mensagem: "Cor inválida",
    };
  }

  if (!esperandoJogada) {
    return {
      ...estado(),
      errou: false,
      bloqueado: true,
      mensagem: "Aguarde a sequência terminar",
    };
  }

  if (sequencia.length === 0) {
    iniciarJogo();
  }

  if (origem === "remoto") {
    adicionarEvento("cor", { cor: numero });
  }

  if (numero === sequencia[posicaoJogador]) {
    posicaoJogador++;

    if (posicaoJogador === sequencia.length) {
      nivel++;
      recorde = Math.max(recorde, nivel - 1);
      posicaoJogador = 0;
      novaCor();
      mensagem = "Acertou! Próximo nível";
      esperandoJogada = false;

      adicionarEvento("proximoNivel", {
        sequencia: [...sequencia],
      });

      liberarJogadaDepoisDaSequencia();
    } else {
      mensagem = "Cor certa, continue";
      esperandoJogada = true;
    }

    return {
      ...estado(),
      errou: false,
    };
  }

  const nivelFinal = nivel;
  recorde = Math.max(recorde, nivelFinal - 1);

  iniciarJogo();

  mensagem = `Errou! Você chegou ao nível ${nivelFinal}. Reiniciando...`;

  adicionarEvento("erro", {
    sequencia: [...sequencia],
    nivelFinal,
  });

  return {
    ...estado(),
    errou: true,
  };
}

function estado() {
  const memoriaMB = Math.round(process.memoryUsage().rss / 1024 / 1024);

  return {
    nivel,
    recorde,
    memoria: `${memoriaMB}MB`,
    mensagem,
    sequencia,
    cores,
    ultimoEventoId,
    ESPERANDO_JOGADA: esperandoJogada,
  };
}

iniciarJogo();

app.get("/", (req, res) => {
  res.send(`
<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8" />
  <title>LC Sistemas - Genius</title>
  <style>
    body {
      font-family: Arial, sans-serif;
      background: #111;
      color: white;
      text-align: center;
      margin: 0;
      padding: 30px;
    }

    h1 {
      font-size: 42px;
      margin-bottom: 10px;
    }

    #info {
      font-size: 20px;
      margin-bottom: 20px;
    }

    #mensagem {
      font-size: 22px;
      margin: 20px;
      color: #00ffcc;
    }

    .genius {
      display: grid;
      grid-template-columns: 150px 150px;
      gap: 15px;
      justify-content: center;
      margin-top: 30px;
    }

    button.cor {
      width: 150px;
      height: 150px;
      border: none;
      border-radius: 20px;
      cursor: pointer;
      opacity: 0.45;
      font-size: 20px;
      font-weight: bold;
      color: white;
      transition: all 0.18s ease;
      box-shadow: inset 0 0 25px rgba(0,0,0,0.6);
      filter: brightness(0.65);
    }

    button.cor:active,
    button.ativo {
      opacity: 1;
      transform: scale(1.06);
      filter: brightness(1.8);
      box-shadow:
        0 0 25px white,
        0 0 45px currentColor,
        inset 0 0 10px rgba(255,255,255,0.8);
    }

    button.todos-ativos {
      opacity: 1;
      transform: scale(1.05);
      filter: brightness(2);
      box-shadow:
        0 0 35px white,
        inset 0 0 10px rgba(255,255,255,0.9);
    }

    .verde {
      background: #006400;
      color: #00ff00;
    }

    .verde.ativo {
      background: #39ff14;
      color: white;
    }

    .vermelho {
      background: #7a0000;
      color: #ff3333;
    }

    .vermelho.ativo {
      background: #ff1a1a;
      color: white;
    }

    .amarelo {
      background: #806000;
      color: #ffd700;
    }

    .amarelo.ativo {
      background: #ffff33;
      color: #111;
    }

    .azul {
      background: #000080;
      color: #3399ff;
    }

    .azul.ativo {
      background: #33ccff;
      color: white;
    }
  </style>
</head>
<body>
  <h1>LC SISTEMAS</h1>

  <div id="info">
    Nível: <span id="nivel">1</span>.
    Recorde: <span id="recorde">0</span>.
    Memória utilizada: <span id="memoria">0MB</span>
  </div>

  <div id="mensagem">Memorize a sequência</div>

  <div class="genius">
    <button class="cor verde" onclick="enviarCorLocal(1)">Verde</button>
    <button class="cor vermelho" onclick="enviarCorLocal(2)">Vermelho</button>
    <button class="cor amarelo" onclick="enviarCorLocal(3)">Amarelo</button>
    <button class="cor azul" onclick="enviarCorLocal(4)">Azul</button>
  </div>

  <script>
    let audioContext;
    let bloqueado = false;
    let ultimoEventoRecebido = 0;
    let reproduzindoSequencia = false;
    let pollingLigado = false;

    const notas = {
      1: 261.63,
      2: 329.63,
      3: 392.00,
      4: 523.25
    };

    function iniciarAudio() {
      if (!audioContext) {
        audioContext = new (window.AudioContext || window.webkitAudioContext)();
      }

      if (audioContext.state === "suspended") {
        audioContext.resume();
      }
    }

    document.body.addEventListener("click", iniciarAudio, { once: true });

    function tocarNota(cor, duracao = 300) {
      iniciarAudio();

      if (!audioContext) return;

      const oscillator = audioContext.createOscillator();
      const gainNode = audioContext.createGain();

      oscillator.type = "sine";
      oscillator.frequency.setValueAtTime(notas[cor], audioContext.currentTime);

      gainNode.gain.setValueAtTime(0.22, audioContext.currentTime);
      gainNode.gain.exponentialRampToValueAtTime(
        0.001,
        audioContext.currentTime + duracao / 1000
      );

      oscillator.connect(gainNode);
      gainNode.connect(audioContext.destination);

      oscillator.start();
      oscillator.stop(audioContext.currentTime + duracao / 1000);
    }

    function tocarSomErro() {
      iniciarAudio();

      if (!audioContext) return;

      const oscillator = audioContext.createOscillator();
      const gainNode = audioContext.createGain();

      oscillator.type = "sawtooth";
      oscillator.frequency.setValueAtTime(180, audioContext.currentTime);
      oscillator.frequency.exponentialRampToValueAtTime(
        70,
        audioContext.currentTime + 0.6
      );

      gainNode.gain.setValueAtTime(0.35, audioContext.currentTime);
      gainNode.gain.exponentialRampToValueAtTime(
        0.001,
        audioContext.currentTime + 0.6
      );

      oscillator.connect(gainNode);
      gainNode.connect(audioContext.destination);

      oscillator.start();
      oscillator.stop(audioContext.currentTime + 0.6);
    }

    async function carregarJogo() {
      const res = await fetch("/iniciar");
      const data = await res.json();

      ultimoEventoRecebido = data.ultimoEventoId;
      atualizarTela(data);

      setTimeout(() => {
        tocarSequencia(data.sequencia);
        pollingLigado = true;
      }, 2000);
    }

    async function enviarCorLocal(cor) {
      if (bloqueado) return;

      acenderLed(cor, true);

      const res = await fetch("/cor-local/" + cor);
      const data = await res.json();

      ultimoEventoRecebido = data.ultimoEventoId;
      atualizarTela(data);

      if (data.bloqueado) {
        return;
      }

      if (data.errou) {
        bloqueado = true;

        setTimeout(() => {
          animarErro(() => {
            atualizarTela(data);
            tocarSequencia(data.sequencia);
          });
        }, 300);

        return;
      }

      if (data.mensagem.includes("Próximo")) {
        bloqueado = true;

        setTimeout(() => {
          tocarSequencia(data.sequencia);
        }, 2000);
      }
    }

    async function buscarEventosRemotos() {
      if (!pollingLigado || reproduzindoSequencia) return;

      try {
        const res = await fetch("/eventos?desde=" + ultimoEventoRecebido);
        const data = await res.json();

        if (data.eventos.length > 0) {
          for (const evento of data.eventos) {
            ultimoEventoRecebido = evento.id;
            processarEvento(evento);
          }
        }

        atualizarTela(data.estado);
      } catch (erro) {
        console.log("Erro ao buscar eventos:", erro.message);
      }
    }

    function processarEvento(evento) {
      if (evento.tipo === "cor") {
        acenderLed(evento.dados.cor, true);
      }

      if (evento.tipo === "proximoNivel") {
        bloqueado = true;

        setTimeout(() => {
          tocarSequencia(evento.dados.sequencia);
        }, 2000);
      }

      if (evento.tipo === "erro") {
        bloqueado = true;

        setTimeout(() => {
          animarErro(() => {
            tocarSequencia(evento.dados.sequencia);
          });
        }, 300);
      }
    }

    function atualizarTela(data) {
      document.getElementById("nivel").innerText = data.nivel;
      document.getElementById("recorde").innerText = data.recorde;
      document.getElementById("memoria").innerText = data.memoria;
      document.getElementById("mensagem").innerText = data.mensagem;
    }

    function tocarSequencia(sequencia) {
      if (reproduzindoSequencia) return;

      reproduzindoSequencia = true;
      bloqueado = true;

      let tempo = 0;

      sequencia.forEach(cor => {
        setTimeout(() => {
          acenderLed(cor, true);
        }, tempo);

        tempo += 700;
      });

      setTimeout(() => {
        reproduzindoSequencia = false;
        bloqueado = false;
        document.getElementById("mensagem").innerText = "Sua vez";
      }, tempo + 200);
    }

    function acenderLed(cor, comSom = true) {
      const classes = {
        1: "verde",
        2: "vermelho",
        3: "amarelo",
        4: "azul"
      };

      const botao = document.querySelector("." + classes[cor]);

      if (!botao) return;

      botao.classList.remove("ativo");

      setTimeout(() => {
        botao.classList.add("ativo");

        if (comSom) {
          tocarNota(cor);
        }

        setTimeout(() => {
          botao.classList.remove("ativo");
        }, 420);
      }, 20);
    }

    function animarErro(callback) {
      let vezes = 0;
      const botoes = document.querySelectorAll(".cor");

      tocarSomErro();

      const intervalo = setInterval(() => {
        botoes.forEach(botao => {
          botao.classList.toggle("todos-ativos");
          botao.classList.toggle("ativo");
        });

        vezes++;

        if (vezes >= 8) {
          clearInterval(intervalo);

          botoes.forEach(botao => {
            botao.classList.remove("todos-ativos");
            botao.classList.remove("ativo");
          });

          setTimeout(() => {
            callback();
          }, 300);
        }
      }, 180);
    }

    window.onload = carregarJogo;

    setInterval(buscarEventosRemotos, 250);
  </script>
</body>
</html>
  `);
});

app.get("/iniciar", (req, res) => {
  iniciarJogo();
  eventos = [];
  ultimoEventoId = 0;
  res.json(estado());
});

app.get("/estado", (req, res) => {
  res.json(estado());
});

app.get("/momento", (req, res) => {
  res.json({
    ESPERANDO_JOGADA: esperandoJogada,
  });
});

app.get("/eventos", (req, res) => {
  const desde = Number(req.query.desde || 0);
  const novosEventos = eventos.filter(evento => evento.id > desde);

  res.json({
    eventos: novosEventos,
    estado: estado(),
  });
});

app.get("/cor/:id", (req, res) => {
  const resultado = jogar(req.params.id, "remoto");
  res.json(resultado);
});

app.get("/cor-local/:id", (req, res) => {
  const resultado = jogar(req.params.id, "local");
  res.json(resultado);
});

app.listen(PORT, () => {
  console.log("Jogo Genius rodando em http://localhost:" + PORT);
  console.log("Rotas remotas:");
  console.log("GET /cor/1 verde");
  console.log("GET /cor/2 vermelho");
  console.log("GET /cor/3 amarelo");
  console.log("GET /cor/4 azul");
  console.log("GET /momento");
});