/*
 * Taskify browser script: drag-and-drop board, live updates over Server-Sent Events,
 * task dialog (comments, assignee, activity) and notifications.
 *
 * Security: all server data is inserted with textContent / value, never innerHTML,
 * so user text can never run as markup (FR-011). State-changing requests carry the
 * Django CSRF token. The server re-validates everything.
 */
(function () {
  "use strict";

  var COLUMNS = [
    ["todo", "To Do"],
    ["in_progress", "In Progress"],
    ["in_review", "In Review"],
    ["done", "Done"],
  ];
  var board = document.getElementById("board");
  var projectId = board ? board.dataset.projectId : null;
  var csrf = (document.querySelector('meta[name="csrf-token"]') || {}).content;
  var users = {};
  var openTaskId = null;
  var refreshTimer = null;
  var hadError = false;

  var peopleEl = document.getElementById("people-data");
  if (peopleEl) {
    JSON.parse(peopleEl.textContent).forEach(function (u) { users[u.id] = u.name; });
  }

  function el(tag, props, children) {
    var node = document.createElement(tag);
    Object.keys(props || {}).forEach(function (k) {
      if (k === "text") node.textContent = props[k];
      else if (k === "class") node.className = props[k];
      else if (k === "data") Object.keys(props[k]).forEach(function (d) { node.dataset[d] = props[k][d]; });
      else node.setAttribute(k, props[k]);
    });
    (children || []).forEach(function (c) { node.appendChild(c); });
    return node;
  }

  function api(method, url, body) {
    var opts = {
      method: method,
      credentials: "same-origin",
      headers: { "X-CSRFToken": csrf, "X-Requested-With": "fetch", "Content-Type": "application/json" },
    };
    if (body !== undefined) opts.body = JSON.stringify(body);
    return fetch(url, opts).then(function (r) {
      return r.json().catch(function () { return {}; }).then(function (data) {
        if (!r.ok) throw new Error(data.error || "Something went wrong. Please try again.");
        return data;
      });
    });
  }

  function showError(message) {
    var box = document.getElementById("task-dialog-error");
    var dialog = document.getElementById("task-dialog");
    if (box && dialog && dialog.open) {
      box.textContent = message;
      box.classList.remove("hidden");
    } else {
      window.alert(message);
    }
  }

  /* ---------- board rendering ---------- */

  function renderCard(task, status) {
    var assignee = task.assignee_id ? users[task.assignee_id] || "User " + task.assignee_id : null;
    var select = el("select", { data: { moveTask: task.id } });
    COLUMNS.forEach(function (c) {
      var opt = el("option", { value: c[0], text: c[1] });
      if (c[0] === status) opt.selected = true;
      select.appendChild(opt);
    });
    return el("li", { class: "card", draggable: "true", data: { taskId: task.id } }, [
      el("button", { type: "button", class: "card-title", text: task.title, data: { openTask: task.id } }),
      el("span", { class: "assignee" + (assignee ? "" : " none"), text: assignee || "Unassigned" }),
      el("label", { class: "move", text: "Move to " }, [select]),
    ]);
  }

  function renderBoard(data) {
    users = Object.assign({}, users, data.users || {});
    COLUMNS.forEach(function (c) {
      var section = board.querySelector('.column[data-status="' + c[0] + '"]');
      var list = section.querySelector(".cards");
      var tasks = data.columns[c[0]];
      list.textContent = "";
      tasks.forEach(function (t) { list.appendChild(renderCard(t, c[0])); });
      if (!tasks.length) list.appendChild(el("li", { class: "empty", text: "No tasks" }));
      section.querySelector(".count").textContent = String(tasks.length);
    });
  }

  function refreshBoard() {
    if (!board) return Promise.resolve();
    return fetch("/projects/" + projectId + "/board.json", { credentials: "same-origin" })
      .then(function (r) { return r.ok ? r.json() : Promise.reject(); })
      .then(renderBoard)
      .catch(function () {});
  }

  function moveTask(taskId, status, position) {
    var body = { status: status };
    if (position !== null && position !== undefined) body.position = position;
    return api("POST", "/tasks/" + taskId + "/move/", body)
      .catch(function (err) { window.alert(err.message); })
      .then(refreshBoard);
  }

  if (board) {
    var dragged = null;
    board.addEventListener("dragstart", function (e) {
      var card = e.target.closest && e.target.closest(".card");
      if (!card) return;
      dragged = card;
      e.dataTransfer.setData("text/plain", card.dataset.taskId);
      e.dataTransfer.effectAllowed = "move";
    });
    board.addEventListener("dragend", function () { dragged = null; });
    board.addEventListener("dragover", function (e) {
      if (dragged && e.target.closest(".column")) e.preventDefault();
    });
    board.addEventListener("drop", function (e) {
      var column = e.target.closest(".column");
      if (!dragged || !column) return;
      e.preventDefault();
      var cards = Array.prototype.filter.call(column.querySelectorAll(".card"), function (c) { return c !== dragged; });
      var position = null;
      for (var i = 0; i < cards.length; i++) {
        var box = cards[i].getBoundingClientRect();
        if (e.clientY < box.top + box.height / 2) { position = i; break; }
      }
      moveTask(dragged.dataset.taskId, column.dataset.status, position);
      dragged = null;
    });
    board.addEventListener("change", function (e) {
      var select = e.target.closest("[data-move-task]");
      if (select) moveTask(select.dataset.moveTask, select.value, null);
    });
    board.addEventListener("click", function (e) {
      var btn = e.target.closest("[data-open-task]");
      if (btn) openTask(btn.dataset.openTask);
    });
  }

  /* ---------- task dialog ---------- */

  var dialog = document.getElementById("task-dialog");

  function fmt(iso) { return new Date(iso).toLocaleString(); }

  function describeActivity(a) {
    var who = users[a.actor_id] || "User " + a.actor_id;
    var name = function (id) { return users[id] || "User " + id; };
    switch (a.action) {
      case "created": return who + " created the task";
      case "moved": return who + " moved it from " + a.from_value + " to " + a.to_value;
      case "assigned": return who + " assigned it to " + name(a.to_value);
      case "unassigned": return who + " cleared the assignee";
      default: return who + " commented";
    }
  }

  function renderDialog(task) {
    users = Object.assign({}, users, task.users || {});
    document.getElementById("task-dialog-title").textContent = task.title;
    document.getElementById("task-dialog-description").textContent = task.description || "";
    var sel = document.getElementById("task-dialog-assignee");
    sel.textContent = "";
    sel.appendChild(el("option", { value: "", text: "Unassigned" }));
    Object.keys(users).forEach(function (id) {
      var opt = el("option", { value: id, text: users[id] });
      if (String(task.assignee_id) === id) opt.selected = true;
      sel.appendChild(opt);
    });
    var comments = document.getElementById("task-comments");
    comments.textContent = "";
    task.comments.forEach(function (c) {
      comments.appendChild(el("li", {}, [
        el("strong", { text: users[c.author_id] || "User " + c.author_id }),
        el("time", { text: " " + fmt(c.created_at) }),
        el("p", { text: c.body }),
      ]));
    });
    var activity = document.getElementById("task-activity");
    activity.textContent = "";
    task.activity.forEach(function (a) {
      activity.appendChild(el("li", { text: describeActivity(a) + " (" + fmt(a.created_at) + ")" }));
    });
  }

  function loadTask(taskId) {
    return fetch("/tasks/" + taskId + "/", { credentials: "same-origin" })
      .then(function (r) { return r.ok ? r.json() : Promise.reject(); })
      .then(renderDialog)
      .catch(function () {});
  }

  function openTask(taskId) {
    openTaskId = taskId;
    document.getElementById("task-dialog-error").classList.add("hidden");
    loadTask(taskId).then(function () { if (dialog.showModal && !dialog.open) dialog.showModal(); });
  }

  if (dialog) {
    document.getElementById("task-dialog-close").addEventListener("click", function () { dialog.close(); });
    dialog.addEventListener("close", function () { openTaskId = null; });
    document.getElementById("task-dialog-assignee").addEventListener("change", function (e) {
      var value = e.target.value;
      api("POST", "/tasks/" + openTaskId + "/assign/", { assignee_id: value === "" ? null : Number(value) })
        .catch(function (err) { showError(err.message); })
        .then(function () { return Promise.all([loadTask(openTaskId), refreshBoard()]); });
    });
    document.getElementById("comment-form").addEventListener("submit", function (e) {
      e.preventDefault();
      var input = document.getElementById("comment-body");
      api("POST", "/tasks/" + openTaskId + "/comments/", { body: input.value })
        .then(function () { input.value = ""; document.getElementById("task-dialog-error").classList.add("hidden"); })
        .catch(function (err) { showError(err.message); })
        .then(function () { return loadTask(openTaskId); });
    });
  }

  /* ---------- notifications ---------- */

  function refreshBadge() {
    if (!document.getElementById("unread-badge")) return;
    fetch("/notifications.json?unread=true", { credentials: "same-origin" })
      .then(function (r) { return r.ok ? r.json() : Promise.reject(); })
      .then(function (list) {
        var badge = document.getElementById("unread-badge");
        badge.textContent = String(list.length);
        badge.classList.toggle("hidden", list.length === 0);
      })
      .catch(function () {});
  }

  function renderNotifications(list) {
    var ul = document.getElementById("notification-list");
    if (!ul) return;
    ul.textContent = "";
    list.forEach(function (n) {
      var li = el("li", { class: "notification " + (n.read ? "read" : "unread"), data: { notificationId: n.id } }, [
        el("span", { class: "msg", text: n.message }),
        el("time", { text: fmt(n.created_at) }),
      ]);
      if (n.read) {
        li.appendChild(el("span", { class: "state", text: "Read" }));
      } else {
        li.appendChild(el("button", { type: "button", "data-mark-read": "", text: "Mark as read" }));
      }
      ul.appendChild(li);
    });
  }

  function refreshNotifications() {
    fetch("/notifications.json", { credentials: "same-origin" })
      .then(function (r) { return r.ok ? r.json() : Promise.reject(); })
      .then(renderNotifications)
      .catch(function () {});
  }

  var noteList = document.getElementById("notification-list");
  if (noteList) {
    noteList.addEventListener("submit", function (e) {
      var li = e.target.closest("[data-notification-id]");
      if (!li) return;
      e.preventDefault();
      api("POST", "/notifications/" + li.dataset.notificationId + "/read/")
        .then(function () { refreshNotifications(); refreshBadge(); })
        .catch(function (err) { window.alert(err.message); });
    });
    noteList.addEventListener("click", function (e) {
      var btn = e.target.closest("button[data-mark-read]");
      var li = btn && btn.closest("[data-notification-id]");
      if (!li || btn.form) return;
      api("POST", "/notifications/" + li.dataset.notificationId + "/read/")
        .then(function () { refreshNotifications(); refreshBadge(); })
        .catch(function (err) { window.alert(err.message); });
    });
  }

  /* ---------- live updates ---------- */

  function scheduleRefresh() {
    clearTimeout(refreshTimer);
    refreshTimer = setTimeout(function () {
      refreshBoard();
      if (openTaskId) loadTask(openTaskId);
    }, 100);
  }

  function setConnection(ok) {
    var status = document.getElementById("connection-status");
    if (status) status.classList.toggle("hidden", ok);
  }

  if (document.body.dataset.userId && window.EventSource) {
    var source = new EventSource("/events/");
    ["task_created", "task_moved", "task_assigned", "comment_added"].forEach(function (type) {
      source.addEventListener(type, function (e) {
        var data = JSON.parse(e.data);
        if (!board || String(data.project_id) === String(projectId)) scheduleRefresh();
      });
    });
    source.addEventListener("notification_created", function () {
      refreshBadge();
      refreshNotifications();
    });
    source.onopen = function () {
      setConnection(true);
      if (hadError) {
        hadError = false;
        scheduleRefresh();
        refreshBadge();
        refreshNotifications();
      }
    };
    source.onerror = function () {
      hadError = true;
      setConnection(false);
    };
  }
})();
