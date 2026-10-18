// "Get listed" form: check the handle on Codeforces, pick a team per contest, review, submit.
(async () => {
  const shell = document.getElementById("form");
  const data = await (await fetch(shell.dataset.src)).json();
  const $ = (id) => document.getElementById(id);
  const HANDLE = /^[A-Za-z0-9_.-]{3,24}$/;
  const OTHER = "__other__";
  let person = null;  // the verified Codeforces user

  // ---------- Codeforces: at most one request every two seconds, as its API asks ----------
  let queue = Promise.resolve();
  const cache = new Map();
  function lookup(handle) {
    const key = handle.toLowerCase();
    if (!cache.has(key)) {
      const result = queue.then(async () => {
        const reply = await (await fetch(`https://codeforces.com/api/user.info?handles=${encodeURIComponent(handle)}`)).json();
        if (reply.status === "OK") return reply.result[0];
        if (/not found/i.test(reply.comment || "")) return null;
        throw new Error(reply.comment || "Codeforces did not answer");
      });
      queue = result.catch(() => {}).then(() => new Promise((resolve) => setTimeout(resolve, 2100)));
      cache.set(key, result);
      result.catch(() => cache.delete(key));  // let a failed check be retried
    }
    return cache.get(key);
  }
  // Codeforces' photo host refuses other sites; codeforces.com serves the same file.
  const photoUrl = (url) => (url && !url.includes("no-title") ? url.replace("https://userpic.codeforces.org/", "https://codeforces.com/userpic.codeforces.org/") : "");

  const element = (tag, attributes = {}, ...children) => {
    const node = document.createElement(tag);
    for (const [name, value] of Object.entries(attributes)) {
      if (name === "class") node.className = value;
      else if (name === "text") node.textContent = value;
      else node.setAttribute(name, value);
    }
    node.append(...children);
    return node;
  };
  const showError = (id, message) => { $(id).textContent = message; $(id).hidden = !message; };

  // ---------- Steps ----------
  function goTo(step) {
    for (const section of shell.querySelectorAll(".form-step")) section.hidden = section.dataset.step !== String(step);
    for (const item of shell.querySelectorAll(".steps li")) {
      if (item.dataset.step === String(step)) item.setAttribute("aria-current", "step");
      else item.removeAttribute("aria-current");
      item.classList.toggle("done", Number(item.dataset.step) < step);
    }
    shell.scrollIntoView({ block: "start", behavior: "smooth" });
  }
  for (const button of shell.querySelectorAll("[data-back]")) button.addEventListener("click", () => goTo(Number(button.dataset.back)));

  // ---------- Step 1: name, handle, institution ----------
  for (const institution of data.institutions) $("institution").append(element("option", { value: institution.id, text: institution.name, "data-search": institution.search }));
  const resetCheck = () => { person = null; $("profile-check").hidden = true; $("to-step2").hidden = true; $("check").hidden = false; };
  $("handle").addEventListener("input", resetCheck);

  $("check").addEventListener("click", async () => {
    showError("step1-error", "");
    const name = $("name").value.trim();
    const handle = $("handle").value.trim();
    if (!name) return showError("step1-error", "Please enter your name.");
    if (!HANDLE.test(handle)) return showError("step1-error", "A Codeforces handle has 3 to 24 letters, digits, and _ . - characters.");
    if (!$("institution").value) return showError("step1-error", "Please choose your institution.");
    $("check").disabled = true;
    $("check").textContent = "Checking…";
    try {
      const user = await lookup(handle);
      if (!user) return showError("step1-error", `Codeforces has no user called ${handle}.`);
      person = user;
      const fullName = [user.firstName, user.lastName].filter(Boolean).join(" ");
      const photo = photoUrl(user.titlePhoto);
      $("profile-check").replaceChildren(
        photo ? element("img", { src: photo, alt: "", referrerpolicy: "no-referrer" }) : element("span", { class: "profile-check-blank", text: user.handle[0].toUpperCase() }),
        element("div", {},
          element("strong", { text: user.handle }),
          element("span", { class: "sub", text: [fullName, user.organization, user.rank && `${user.rank[0].toUpperCase()}${user.rank.slice(1)}`].filter(Boolean).join(" · ") || "No name on Codeforces" }),
          element("span", { class: "sub", text: "Is this your Codeforces account?" })),
      );
      $("profile-check").hidden = false;
      $("check").hidden = true;
      $("to-step2").hidden = false;
    } catch (error) {
      showError("step1-error", "Could not reach Codeforces. Please try again in a moment.");
    } finally {
      $("check").disabled = false;
      $("check").textContent = "Check handle";
    }
  });

  $("to-step2").addEventListener("click", () => { buildContests(); goTo(2); });

  // ---------- Step 2: one card per contest ----------
  let builtFor = "";
  function buildContests() {
    const institution = $("institution").value;
    const key = `${institution}|${person.handle.toLowerCase()}`;
    if (key === builtFor) return;  // keep answers when coming back
    builtFor = key;
    const me = person.handle.toLowerCase();
    const list = $("contest-list");
    list.replaceChildren();
    for (const contest of data.contests) {
      const teams = contest.teams[institution] || [];
      const select = element("select", { "aria-label": `Your team in ${contest.name}` },
        element("option", { value: "", text: "Did not take part" }),
        ...teams.map((team) => element("option", { value: team.name, text: team.name })),
        element("option", { value: OTHER, text: "My team is not listed…" }));
      const other = element("input", { placeholder: "Team name as in the standings", hidden: "" });
      const mates = [0, 1].map(() => {
        const input = element("input", { placeholder: "Teammate's handle (optional)", autocapitalize: "off", spellcheck: "false" });
        const status = element("span", { class: "mate-status", "aria-live": "polite" });
        input.addEventListener("change", () => checkMate(input, status));
        input.addEventListener("input", () => { input.dataset.state = ""; status.textContent = ""; });
        return { input, status, wrap: element("div", { class: "mate" }, input, status) };
      });
      const extra = element("div", { class: "contest-extra", hidden: "" }, other, ...mates.map((mate) => mate.wrap));
      const card = element("div", { class: "contest-card" },
        element("div", { class: "contest-head" },
          element("strong", { text: contest.name }),
          element("span", { class: "muted", text: new Date(contest.date).toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric" }) }),
          contest.standings ? element("a", { href: contest.standings, target: "_blank", rel: "noopener", text: "Standings ↗" }) : ""),
        select, extra);
      card.contest = contest.name;
      card.parts = { select, other, mates };
      select.addEventListener("change", () => {
        extra.hidden = !select.value;
        other.hidden = select.value !== OTHER;
        card.classList.toggle("chosen", Boolean(select.value));
      });
      // Teams already known to include this person are picked, with the teammates we know.
      const known = teams.find((team) => team.members.some((handle) => handle.toLowerCase() === me));
      if (known) {
        select.value = known.name;
        known.members.filter((handle) => handle.toLowerCase() !== me).slice(0, 2).forEach((handle, i) => {
          mates[i].input.value = handle;
          mates[i].input.dataset.state = "ok";
          mates[i].status.textContent = "✓";
        });
        select.dispatchEvent(new Event("change"));
      }
      list.append(card);
    }
  }

  async function checkMate(input, status) {
    const handle = input.value.trim();
    input.value = handle;
    if (!handle) { input.dataset.state = ""; status.textContent = ""; return; }
    if (!HANDLE.test(handle)) { input.dataset.state = "bad"; status.textContent = "Not a valid handle"; return; }
    input.dataset.state = "checking";
    status.textContent = "Checking…";
    try {
      const user = await lookup(handle);
      if (input.value.trim() !== handle) return;  // changed while checking
      input.dataset.state = user ? "ok" : "bad";
      if (user) input.value = user.handle;
      status.textContent = user ? "✓" : "Not on Codeforces";
    } catch (error) {
      input.dataset.state = "bad";
      status.textContent = "Could not check; try again";
    }
  }

  const answers = () => [...$("contest-list").children]
    .filter((card) => card.parts.select.value)
    .map((card) => ({
      contest: card.contest,
      team: card.parts.select.value === OTHER ? card.parts.other.value.trim() : card.parts.select.value,
      listed: card.parts.select.value !== OTHER,
      teammates: card.parts.mates.map((mate) => mate.input.value.trim()).filter(Boolean),
    }));

  $("to-step3").addEventListener("click", async () => {
    showError("step2-error", "");
    const cards = [...$("contest-list").children].filter((card) => card.parts.select.value);
    const mates = cards.flatMap((card) => card.parts.mates).filter((mate) => mate.input.value.trim());
    for (const mate of mates) if (mate.input.dataset.state !== "ok") await checkMate(mate.input, mate.status);
    if (mates.some((mate) => mate.input.dataset.state !== "ok")) return showError("step2-error", "Fix or clear the teammates' handles marked in red.");
    if (cards.some((card) => card.parts.select.value === OTHER && !card.parts.other.value.trim())) return showError("step2-error", "Type the team name for each contest where your team is not listed.");
    if (!cards.length) return showError("step2-error", "Pick your team in at least one contest.");
    const rows = answers();
    $("review").replaceChildren(
      element("p", {}, element("strong", { text: $("name").value.trim() }), ` · ${person.handle} · ${$("institution").selectedOptions[0].text}`),
      element("div", { class: "table-wrap" }, element("table", { class: "table" },
        element("thead", {}, element("tr", {}, element("th", { text: "Contest" }), element("th", { text: "Team" }), element("th", { text: "Teammates" }))),
        element("tbody", {}, ...rows.map((row) => element("tr", {},
          element("td", { text: row.contest }),
          element("td", { text: row.listed ? row.team : `${row.team} (not listed)` }),
          element("td", { text: row.teammates.join(", ") || "—" })))))),
    );
    goTo(3);
  });

  // ---------- Step 3: submit ----------
  $("submit").addEventListener("click", async () => {
    showError("step3-error", "");
    const values = {
      Name: $("name").value.trim(),
      Handle: person.handle,
      Institution: $("institution").value,
      Teams: JSON.stringify(answers().map(({ contest, team, teammates }) => ({ contest, team, teammates }))),
    };
    const { action, entries } = data.settings;
    $("submit").disabled = true;
    try {
      if (action) {
        // Google Forms takes a plain form post; its reply cannot be read from another site.
        const body = new URLSearchParams();
        for (const question of data.questions) body.append(entries[question], values[question]);
        await fetch(action, { method: "POST", mode: "no-cors", body });
      } else {
        // Not connected to a form yet: hand over the answers as a file in the same layout.
        const quote = (value) => `"${String(value).replace(/"/g, '""')}"`;
        const csv = [["Timestamp", ...data.questions], [new Date().toISOString(), ...data.questions.map((q) => values[q])]]
          .map((row) => row.map(quote).join(",")).join("\n") + "\n";
        const link = element("a", { href: URL.createObjectURL(new Blob([csv], { type: "text/csv" })), download: `biscuit-${person.handle}.csv` });
        document.body.append(link);
        link.click();
        link.remove();
        $("done-message").textContent = "Your answers were saved as a file. Send it to the site's maintainer.";
      }
      goTo(4);
    } catch (error) {
      showError("step3-error", "Could not send your answers. Please check your connection and try again.");
    } finally {
      $("submit").disabled = false;
    }
  });
})();
