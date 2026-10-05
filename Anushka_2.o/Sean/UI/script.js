const statusBox = document.getElementById("status");
const canvas = document.getElementById("wave");

const ctx = canvas.getContext("2d");

canvas.width = 900;
canvas.height = 250;

let speaking = false;

let textBox =
document.getElementById("speech");

const ws =
new WebSocket(
"ws://localhost:8765"
);

ws.onmessage = (event)=>{

const msg =
JSON.parse(event.data);

if(msg.type==="start"){

statusBox.innerText =
"SPEAKING";
speaking = true;

textBox.innerText =
msg.text;

}

if(msg.type==="stop"){


statusBox.innerText =
"IDLE";
speaking = false;

}

};

function animate(){

ctx.clearRect(
0,
0,
canvas.width,
canvas.height
);

ctx.beginPath();

for(let x=0;x<canvas.width;x++){

let amp =
speaking ? 70 : 8;

let y =
125 +
Math.sin(
x*0.03 +
Date.now()*0.01
) * amp;

ctx.lineTo(x,y);

}
ctx.lineWidth = 4;
ctx.shadowBlur = 20;
ctx.shadowColor = "#00ffff";
ctx.stroke();

requestAnimationFrame(
animate
);

}

animate();