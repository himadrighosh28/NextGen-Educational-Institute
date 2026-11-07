(function () {
    const root = document.documentElement;
    root.classList.add("page-restoring");
    window.addEventListener("pageshow", function (event) {
        if (event.persisted) {
            document.querySelectorAll(
                ".application-form, .query-form"
            ).forEach(function (form) {
                form.reset();
            });
        }
        requestAnimationFrame(function () {
            root.classList.remove("page-restoring");
        });
    });
})();