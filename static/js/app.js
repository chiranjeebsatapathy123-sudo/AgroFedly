const drawer=document.getElementById("drawer"),backdrop=document.getElementById("backdrop");
const open=()=>{drawer?.classList.add("open");backdrop?.classList.add("show")};
const close=()=>{drawer?.classList.remove("open");backdrop?.classList.remove("show")};
document.getElementById("menuBtn")?.addEventListener("click",open);
document.getElementById("closeMenu")?.addEventListener("click",close);
backdrop?.addEventListener("click",close);
document.addEventListener("keydown",e=>{if(e.key==="Escape")close()});
setTimeout(()=>document.querySelectorAll(".message").forEach(x=>x.remove()),5000);
