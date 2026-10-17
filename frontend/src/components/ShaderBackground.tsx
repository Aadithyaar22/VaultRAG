import { useEffect, useRef } from "react";

// Fog shader adapted from the Stitch "modern showcase" export (code.html). Behaviour added for the app:
// honours prefers-reduced-motion (renders a single still frame), pauses while the tab is hidden, renders at
// reduced resolution (it is a soft fog), and falls back silently when WebGL is unavailable.
const VS = `attribute vec2 a_position; void main(){ gl_Position = vec4(a_position, 0.0, 1.0); }`;
const FS = `precision highp float;
uniform float u_time; uniform vec2 u_resolution; uniform vec2 u_mouse;
vec3 mod289(vec3 x){return x-floor(x*(1.0/289.0))*289.0;}
vec2 mod289(vec2 x){return x-floor(x*(1.0/289.0))*289.0;}
vec3 permute(vec3 x){return mod289(((x*34.0)+1.0)*x);}
float snoise(vec2 v){
  const vec4 C=vec4(0.211324865405187,0.366025403784439,-0.577350269189626,0.024390243902439);
  vec2 i=floor(v+dot(v,C.yy)); vec2 x0=v-i+dot(i,C.xx);
  vec2 i1=(x0.x>x0.y)?vec2(1.0,0.0):vec2(0.0,1.0);
  vec4 x12=x0.xyxy+C.xxzz; x12.xy-=i1; i=mod289(i);
  vec3 p=permute(permute(i.y+vec3(0.0,i1.y,1.0))+i.x+vec3(0.0,i1.x,1.0));
  vec3 m=max(0.5-vec3(dot(x0,x0),dot(x12.xy,x12.xy),dot(x12.zw,x12.zw)),0.0); m=m*m; m=m*m;
  vec3 x=2.0*fract(p*C.www)-1.0; vec3 h=abs(x)-0.5; vec3 ox=floor(x+0.5); vec3 a0=x-ox;
  m*=1.79284291400159-0.85373472095314*(a0*a0+h*h);
  vec3 g; g.x=a0.x*x0.x+h.x*x0.y; g.yz=a0.yz*x12.xz+h.yz*x12.yw;
  return 130.0*dot(m,g);
}
float fbm(vec2 p){float t=0.0,a=0.5,f=1.0; for(int i=0;i<4;i++){t+=snoise(p*f)*a; f*=2.05; a*=0.5;} return t;}
void main(){
  vec2 uv=gl_FragCoord.xy/u_resolution.xy;
  vec2 p=(gl_FragCoord.xy*2.0-u_resolution.xy)/min(u_resolution.x,u_resolution.y);
  vec2 mouse=(u_mouse*2.0-u_resolution.xy)/min(u_resolution.x,u_resolution.y);
  float t=u_time*0.35;
  vec2 q=vec2(fbm(p+vec2(t*0.45,t*0.22)), fbm(p+vec2(-t*0.38,t*0.3)));
  vec2 r=vec2(fbm(p+1.9*q+vec2(1.7,9.2)+0.22*t), fbm(p+1.9*q+vec2(8.3,2.8)+0.18*t));
  float mDist=length(p-mouse);
  if(length(u_mouse)>10.0){ float w=sin(mDist*9.0-u_time*3.0)*exp(-mDist*1.8)*0.35; r+=normalize(p-mouse+0.001)*w; }
  float f=fbm(p+2.5*r+vec2(0.1*sin(t),0.1*cos(t)));
  float fog1=fbm(p*1.3+vec2(t*0.15,t*0.08)+r*0.5)*0.5+0.5;
  float fog2=fbm(p*2.1-vec2(t*0.12,-t*0.1)+q*0.6)*0.5+0.5;
  float fog=mix(fog1,fog2,0.5);
  vec3 col=mix(vec3(0.06,0.09,0.17),vec3(0.09,0.14,0.24),clamp(fog*1.2,0.0,1.0));
  col=mix(col,vec3(0.20,0.45,0.95),clamp(length(r.x),0.0,1.0)*0.55);
  col=mix(col,vec3(0.48,0.28,0.88),clamp(pow(length(r.y),1.8),0.0,1.0)*0.45);
  col=mix(col,vec3(0.0,0.92,0.95),clamp(pow(f*0.5+0.5,2.8),0.0,1.0)*0.65);
  col+=vec3(0.70,0.88,1.0)*smoothstep(0.35,0.85,fog)*0.25;
  col+=vec3(0.85,0.98,1.0)*pow(max(0.0,1.0-abs(f)),6.0)*0.38;
  vec2 g=fract(p*8.0)-0.5; float grid=smoothstep(0.025,0.0,abs(g.x))+smoothstep(0.025,0.0,abs(g.y));
  col+=vec3(0.08,0.25,0.45)*grid*(0.15+0.1*sin(t+p.x));
  col*=1.0-smoothstep(0.5,1.5,length(uv-0.5))*0.45;
  gl_FragColor=vec4(col,1.0);
}`;

export default function ShaderBackground({ dim = 0.72 }: { dim?: number }) {
  const ref = useRef<HTMLCanvasElement>(null);
  useEffect(() => {
    const canvas = ref.current;
    const gl = canvas && (canvas.getContext("webgl") as WebGLRenderingContext | null);
    if (!canvas || !gl) return;
    const compile = (type: number, src: string) => { const s = gl.createShader(type)!; gl.shaderSource(s, src); gl.compileShader(s); return s; };
    const prog = gl.createProgram()!;
    gl.attachShader(prog, compile(gl.VERTEX_SHADER, VS)); gl.attachShader(prog, compile(gl.FRAGMENT_SHADER, FS));
    gl.linkProgram(prog);
    if (!gl.getProgramParameter(prog, gl.LINK_STATUS)) return;
    gl.useProgram(prog);
    gl.bindBuffer(gl.ARRAY_BUFFER, gl.createBuffer());
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 1, -1, -1, 1, 1, 1]), gl.STATIC_DRAW);
    const pos = gl.getAttribLocation(prog, "a_position");
    gl.enableVertexAttribArray(pos); gl.vertexAttribPointer(pos, 2, gl.FLOAT, false, 0, 0);
    const uT = gl.getUniformLocation(prog, "u_time"), uR = gl.getUniformLocation(prog, "u_resolution"), uM = gl.getUniformLocation(prog, "u_mouse");
    const SCALE = 0.5; // fog is soft: render at half resolution
    const size = () => { canvas.width = Math.max(2, Math.floor(canvas.clientWidth * SCALE)); canvas.height = Math.max(2, Math.floor(canvas.clientHeight * SCALE)); };
    size();
    const mouse = { x: 0, y: 0 };
    const onMove = (e: MouseEvent) => { mouse.x = (e.clientX / innerWidth) * canvas.width; mouse.y = (1 - e.clientY / innerHeight) * canvas.height; };
    const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    let raf = 0, alive = true;
    const draw = (t: number) => {
      gl.viewport(0, 0, canvas.width, canvas.height);
      gl.uniform1f(uT, t * 0.001); gl.uniform2f(uR, canvas.width, canvas.height); gl.uniform2f(uM, mouse.x, mouse.y);
      gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);
    };
    const loop = (t: number) => { if (!alive) return; if (!document.hidden) draw(t); raf = requestAnimationFrame(loop); };
    const onResize = () => { size(); if (reduce) draw(8000); };
    window.addEventListener("resize", onResize);
    if (reduce) draw(8000); else { window.addEventListener("mousemove", onMove); raf = requestAnimationFrame(loop); }
    return () => { alive = false; cancelAnimationFrame(raf); window.removeEventListener("resize", onResize); window.removeEventListener("mousemove", onMove); };
  }, []);
  return (
    <div aria-hidden className="pointer-events-none fixed inset-0 -z-10">
      <canvas ref={ref} className="block h-full w-full" />
      <div className="absolute inset-0" style={{ background: `rgba(4,7,17,${dim})` }} />
    </div>
  );
}
