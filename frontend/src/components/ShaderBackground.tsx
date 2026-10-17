import { useEffect, useRef } from "react";

// Live aurora background (WebGL). Evolved from the Stitch fog shader:
//  - four-colour palette (teal / blue / violet / magenta) drifting on slow flow fields
//  - pointer-reactive: the field bends around the cursor, swirls with cursor speed, and glows
//  - ambient drift is user-switchable (defaults to the OS reduced-motion setting); pointer response always works,
//    pauses when the tab is hidden,
//    renders at reduced resolution, and falls back silently when WebGL is unavailable.
const VS = `attribute vec2 a_position; void main(){ gl_Position = vec4(a_position, 0.0, 1.0); }`;
const FS = `precision highp float;
uniform float u_time; uniform vec2 u_res; uniform vec2 u_mouse; uniform float u_energy;
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
float fbm(vec2 p){float t=0.0,a=0.6; for(int i=0;i<2;i++){t+=snoise(p)*a; p=p*1.8+vec2(3.1,1.7); a*=0.5;} return t;}
mat2 rot(float a){float c=cos(a),s=sin(a);return mat2(c,-s,s,c);}
void main(){
  vec2 uv=gl_FragCoord.xy/u_res;
  float asp=u_res.x/u_res.y;
  vec2 p=(uv-0.5)*vec2(asp,1.0)*2.0;
  vec2 m=(u_mouse/u_res-0.5)*vec2(asp,1.0)*2.0;
  float t=u_time*0.12;

  // pointer: lens-bend + swirl that grows with cursor speed
  vec2 d=p-m; float dist=length(d);
  float fall=exp(-dist*dist*2.2);
  p+= -d*fall*0.28;
  p = m + rot(u_energy*1.8*fall)*(p-m);

  // flowing fields
  vec2 q=vec2(fbm(p*0.55+vec2(t,-t*0.7)), fbm(p*0.55+vec2(-t*0.8,t)+4.2));
  vec2 r=vec2(fbm(p*0.6+1.5*q+vec2(1.7,9.2)+t*0.6), fbm(p*0.6+1.5*q+vec2(8.3,2.8)-t*0.5));
  float f=fbm(p*0.5+1.6*r);

  vec3 base  = vec3(0.012,0.020,0.050);
  vec3 teal  = vec3(0.07,0.80,0.74);
  vec3 blue  = vec3(0.16,0.42,1.00);
  vec3 violet= vec3(0.50,0.32,1.00);
  vec3 pink  = vec3(0.96,0.28,0.66);

  vec3 col=base;
  col=mix(col,blue,  smoothstep(-0.3,0.6,q.x)*0.85);
  col=mix(col,teal,  smoothstep(-0.1,0.7,r.y)*0.80);
  col=mix(col,violet,smoothstep(-0.2,0.7,r.x)*0.80);
  col=mix(col,pink,  smoothstep(0.05,0.8,f+0.2*q.y)*0.70);

  // pointer glow whose colour drifts with time; stronger when moving
  vec3 gc=0.5+0.5*cos(6.2831*(vec3(0.0,0.33,0.67)+u_time*0.05));
  col+= mix(vec3(0.25,0.7,0.9),gc,0.6) * exp(-dist*dist*5.5) * (0.20+0.55*u_energy);

  col*= 1.0-smoothstep(0.55,1.6,length(uv-0.5)*1.4)*0.5;                  // vignette
  gl_FragColor=vec4(col,1.0);
}`;

export default function ShaderBackground({ dim = 0.72, ambient = true }: { dim?: number; ambient?: boolean }) {
  const ref = useRef<HTMLCanvasElement>(null);
  const ambientRef = useRef(ambient);
  const kick = useRef<() => void>(() => {});
  useEffect(() => { ambientRef.current = ambient; kick.current(); }, [ambient]);
  useEffect(() => {
    const canvas = ref.current;
    const gl = canvas && (canvas.getContext("webgl", { antialias: false, powerPreference: "low-power" }) as WebGLRenderingContext | null);
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
    const uT = gl.getUniformLocation(prog, "u_time"), uR = gl.getUniformLocation(prog, "u_res"),
          uM = gl.getUniformLocation(prog, "u_mouse"), uE = gl.getUniformLocation(prog, "u_energy");

    const SCALE = 0.5;
    const size = () => { canvas.width = Math.max(2, Math.floor(canvas.clientWidth * SCALE)); canvas.height = Math.max(2, Math.floor(canvas.clientHeight * SCALE)); };
    size();

    // pointer state: target follows the cursor; the shader sees a smoothed position + decaying speed "energy".
    // Pointer response is user-initiated motion, so it works even when ambient drift is off (reduced-motion users).
    const target = { x: canvas.width * 0.5, y: canvas.height * 0.55 };
    const smooth = { x: target.x, y: target.y };
    let energy = 0, raf = 0, alive = true, running = false, last = 0;
    const FROZEN = 9000; // ms: time value used for the still frame when ambient drift is off
    const draw = (t: number) => {
      const dx = target.x - smooth.x, dy = target.y - smooth.y;
      smooth.x += dx * 0.07; smooth.y += dy * 0.07;
      const speed = Math.min(1, Math.hypot(dx, dy) / (canvas.width * 0.25));
      energy = Math.max(speed, energy * 0.96);
      gl.viewport(0, 0, canvas.width, canvas.height);
      gl.uniform1f(uT, (ambientRef.current ? t : FROZEN) * 0.001); gl.uniform2f(uR, canvas.width, canvas.height);
      gl.uniform2f(uM, smooth.x, smooth.y); gl.uniform1f(uE, energy);
      gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);
      return Math.hypot(dx, dy) > 0.6 || energy > 0.01;
    };
    const loop = (t: number) => {
      if (!alive) return;
      let more = ambientRef.current;
      if (!document.hidden && t - last > 30) { last = t; more = draw(t) || more; }
      if (more || document.hidden) raf = requestAnimationFrame(loop); else running = false;
    };
    const ensure = () => { if (!running && alive) { running = true; raf = requestAnimationFrame(loop); } };
    kick.current = ensure;
    const onMove = (e: PointerEvent) => { target.x = (e.clientX / innerWidth) * canvas.width; target.y = (1 - e.clientY / innerHeight) * canvas.height; ensure(); };
    const onResize = () => { size(); draw(performance.now()); };
    window.addEventListener("resize", onResize);
    window.addEventListener("pointermove", onMove);
    draw(performance.now()); ensure();
    return () => { alive = false; kick.current = () => {}; cancelAnimationFrame(raf); window.removeEventListener("resize", onResize); window.removeEventListener("pointermove", onMove); };
  }, []);
  return (
    <div aria-hidden className="pointer-events-none fixed inset-0 -z-10 bg-[#050813]">
      <canvas ref={ref} className="block h-full w-full" style={{ filter: "blur(10px) saturate(125%)", transform: "scale(1.08)" }} />
      <div className="absolute inset-0" style={{ background: `rgba(4,7,17,${dim})` }} />
    </div>
  );
}
