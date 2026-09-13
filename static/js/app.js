const drawer=document.getElementById("drawer"),backdrop=document.getElementById("backdrop");
const openDrawer=()=>{drawer?.classList.add("open");backdrop?.classList.add("show")};
const closeDrawer=()=>{drawer?.classList.remove("open");backdrop?.classList.remove("show")};
document.getElementById("menuBtn")?.addEventListener("click",openDrawer);
document.getElementById("closeMenu")?.addEventListener("click",closeDrawer);
backdrop?.addEventListener("click",closeDrawer);
document.addEventListener("keydown",e=>{if(e.key==="Escape")closeDrawer()});
setTimeout(()=>document.querySelectorAll(".message").forEach(x=>x.remove()),5000);

// Dark Mode Toggle
const themeToggle = document.getElementById("themeToggle");
const currentTheme = localStorage.getItem("theme");

if (currentTheme === "dark") {
    document.body.classList.add("dark-theme");
    if(themeToggle) themeToggle.innerText = "☀️";
}

if(themeToggle) {
    themeToggle.addEventListener("click", () => {
        document.body.classList.toggle("dark-theme");
        let theme = "light";
        if (document.body.classList.contains("dark-theme")) {
            theme = "dark";
            themeToggle.innerText = "☀️";
        } else {
            themeToggle.innerText = "🌙";
        }
        localStorage.setItem("theme", theme);
    });
}
