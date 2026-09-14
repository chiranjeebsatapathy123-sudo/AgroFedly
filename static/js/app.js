const drawer=document.getElementById("drawer"),backdrop=document.getElementById("backdrop");
const openDrawer=()=>{drawer?.classList.add("open");backdrop?.classList.add("show")};
const closeDrawer=()=>{drawer?.classList.remove("open");backdrop?.classList.remove("show")};
document.getElementById("menuBtn")?.addEventListener("click",openDrawer);
document.getElementById("closeMenu")?.addEventListener("click",closeDrawer);
backdrop?.addEventListener("click",closeDrawer);
document.addEventListener("keydown",e=>{if(e.key==="Escape")closeDrawer()});
setTimeout(()=>document.querySelectorAll(".message").forEach(x=>x.remove()),5000);

