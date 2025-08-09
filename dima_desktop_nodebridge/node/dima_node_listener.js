const net = require('net');
const { exec } = require('child_process');

const server = net.createServer((socket) => {
  socket.on('data', (data) => {
    try {
      const command = JSON.parse(data.toString());
      if (command.type === "system_command") {
        console.log("🚀 Выполняю:", command.text);
        exec(command.text, (error, stdout, stderr) => {
          if (error) console.error("❌ Ошибка:", error);
          if (stdout) console.log("📤 STDOUT:", stdout);
          if (stderr) console.log("⚠️ STDERR:", stderr);
        });
      }
    } catch (e) {
      console.error("Ошибка парсинга:", e);
    }
  });
});

server.listen(5555, () => {
  console.log("🎧 Node.js слушает порт 5555 для команд от Димы");
});
