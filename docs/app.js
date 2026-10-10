"use strict";

const chooser = document.getElementById("skill-chooser");
if (chooser) {
  chooser.addEventListener("submit", (event) => {
    event.preventDefault();
    const task = document.getElementById("chooser-task").selectedOptions[0];
    const agent = document.getElementById("chooser-agent").value;
    const target = document.getElementById("chooser-target").value.trim();
    if (!target) {
      document.getElementById("chooser-target").focus();
      return;
    }
    const request = agent === "codex"
      ? `$${task.value}\nReview ${target} without editing files.\nRead the project's instructions and the skill's engineering contract.\nExplain confirmed findings, supporting evidence and checks you could not run.`
      : `/wp-devkit:${task.dataset.command} ${target}\nKeep this review read-only. Explain findings and checks you could not run.`;
    document.getElementById("chooser-prompt").textContent = request;
    document.getElementById("chooser-summary").textContent = `Use ${task.textContent} for this review. Copy the request into your agent.`;
    document.getElementById("chooser-guide").href = task.dataset.guide;
    document.getElementById("chooser-result").hidden = false;
  });
}

// Filtering supplements the complete, server-independent HTML catalog.
document.querySelectorAll("[data-search]").forEach((input) => {
  const group = document.getElementById(input.dataset.search);
  const items = [...group.querySelectorAll("[data-search-item]")];
  const status = document.getElementById(input.dataset.status);
  const empty = document.getElementById(input.dataset.empty);
  const filter = () => {
    const query = input.value.trim().toLocaleLowerCase();
    let visible = 0;
    items.forEach((item) => {
      const matches = item.textContent.toLocaleLowerCase().includes(query);
      item.hidden = !matches;
      if (matches) visible += 1;
    });
    status.textContent = `${visible} of ${items.length} ${input.dataset.kind} shown`;
    empty.hidden = visible !== 0;
  };
  input.addEventListener("input", filter);
  filter();
});

document.querySelectorAll("pre").forEach((block) => {
  const tools = document.createElement("div");
  tools.className = "code-tools";
  const button = document.createElement("button");
  button.type = "button";
  button.className = "copy-button";
  button.textContent = "Copy example";
  button.setAttribute("aria-label", "Copy the preceding code example");
  button.addEventListener("click", async () => {
    try {
      await navigator.clipboard.writeText(block.textContent);
      button.textContent = "Copied";
    } catch {
      const selection = window.getSelection();
      const range = document.createRange();
      range.selectNodeContents(block);
      selection.removeAllRanges();
      selection.addRange(range);
      button.textContent = "Selected — copy manually";
    }
    window.setTimeout(() => { button.textContent = "Copy example"; }, 2500);
  });
  tools.append(button);
  block.after(tools);
});
