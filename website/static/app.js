// Theme switch: remembers the choice; the page starts in the saved or system theme.
document.querySelector(".theme-toggle").addEventListener("click", () => {
  const theme = document.documentElement.dataset.theme === "dark" ? "light" : "dark";
  document.documentElement.dataset.theme = theme;
  try { localStorage.setItem("theme", theme); } catch (e) {}
});

// Rankings: filter by search text and, for contestants, institution.
const search = document.getElementById("search");
const institution = document.getElementById("rankings") && document.getElementById("institution");
if (search) {
  const rows = [...document.querySelectorAll("#rankings tbody tr")];
  const empty = document.getElementById("empty");
  const apply = () => {
    const words = search.value.toLowerCase().trim().split(/\s+/).filter(Boolean);
    const chosen = institution ? institution.value : "";
    let shown = 0;
    for (const row of rows) {
      const visible = words.every((word) => row.dataset.search.includes(word))
        && (!chosen || row.dataset.institution === chosen);
      row.hidden = !visible;
      shown += visible;
    }
    empty.hidden = shown > 0;
  };
  search.addEventListener("input", apply);
  // The chosen institution lives in the address, so institution links and shared URLs open filtered.
  if (institution) institution.addEventListener("change", () => {
    const url = new URL(location.href);
    if (institution.value) url.searchParams.set("institution", institution.value);
    else url.searchParams.delete("institution");
    history.replaceState(null, "", url);
    apply();
  });
  const chosen = new URLSearchParams(location.search).get("institution");
  if (chosen && institution && [...institution.options].some((option) => option.value === chosen)) {
    institution.value = chosen;
    apply();
  }
}

// Rating chart: tooltip on hover and keyboard focus.
const tooltip = document.querySelector(".tooltip");
for (const point of document.querySelectorAll(".chart .point")) {
  const title = point.querySelector("title");
  const show = () => {
    const [heading, detail] = point.dataset.tip.split("|");
    tooltip.replaceChildren();
    const strong = document.createElement("strong");
    strong.textContent = heading;
    tooltip.append(strong, detail);
    const box = point.getBoundingClientRect();
    tooltip.style.left = `${box.left + box.width / 2}px`;
    tooltip.style.top = `${box.top}px`;
    tooltip.hidden = false;
    if (title) title.remove();  // the custom tooltip replaces the browser's
  };
  const hide = () => { tooltip.hidden = true; };
  point.addEventListener("mouseenter", show);
  point.addEventListener("focus", show);
  point.addEventListener("mouseleave", hide);
  point.addEventListener("blur", hide);
}

// Team names: show the members on hover and focus. The card stays open while the
// pointer moves onto it, so its members' profile links can be clicked.
let hideTimer = null;
const hideCard = () => { tooltip.hidden = true; tooltip.classList.remove("card"); };
const hideCardSoon = () => { clearTimeout(hideTimer); hideTimer = setTimeout(hideCard, 250); };
const keepCard = () => clearTimeout(hideTimer);
tooltip.addEventListener("mouseenter", () => { if (tooltip.classList.contains("card")) keepCard(); });
tooltip.addEventListener("mouseleave", () => { if (tooltip.classList.contains("card")) hideCardSoon(); });
for (const label of document.querySelectorAll(".team-label")) {
  const members = label.querySelector(".team-members");
  const show = () => {
    keepCard();
    tooltip.innerHTML = members.innerHTML;
    tooltip.classList.add("card");
    const box = label.getBoundingClientRect();
    tooltip.style.left = `${box.left + box.width / 2}px`;
    tooltip.style.top = `${box.top}px`;
    tooltip.hidden = false;
  };
  label.addEventListener("mouseenter", show);
  label.addEventListener("focus", show);
  label.addEventListener("mouseleave", hideCardSoon);
  label.addEventListener("blur", hideCardSoon);  // late enough for a tap on a member link to land
}
document.addEventListener("keydown", (event) => { if (event.key === "Escape") hideCard(); });
