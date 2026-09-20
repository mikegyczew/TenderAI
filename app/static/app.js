document.addEventListener("DOMContentLoaded", () => {
    checkAuthentication();
    setupSourceMode();
});

async function checkAuthentication() {
    const response = await fetch("/auth/status");
    const data = await response.json();
    setAuthenticatedState(data.authenticated);
}

async function login(event) {
    event.preventDefault();
    const loginError = document.getElementById("loginError");
    loginError.innerText = "";

    try {
        const response = await fetch("/login", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
                username: document.getElementById("username").value,
                password: document.getElementById("password").value
            })
        });

        const data = await response.json();
        if (!response.ok) {
            loginError.innerText = data.detail || "Logowanie nie powiodło się.";
            return;
        }

        window.location.reload();
    } catch (error) {
        loginError.innerText = "Nie udało się połączyć z serwerem.";
        console.error(error);
    }
}

async function logout() {
    await fetch("/logout", { method: "POST" });
    setAuthenticatedState(false);
}

function setAuthenticatedState(authenticated) {
    document.getElementById("loginCard").classList.toggle("hidden", authenticated);
    document.getElementById("analyzerCard").classList.toggle("hidden", !authenticated);
    document.getElementById("logoutButton").classList.toggle("hidden", !authenticated);
    if (!authenticated) {
        document.getElementById("result").classList.add("hidden");
    }
}

function setupSourceMode() {
    document.querySelectorAll('input[name="sourceMode"]').forEach((radio) => {
        radio.addEventListener("change", updateSourceFields);
    });
    updateSourceFields();
}

function updateSourceFields() {
    const sourceMode = document.querySelector('input[name="sourceMode"]:checked').value;
    document.getElementById("textSource").classList.toggle("hidden", sourceMode !== "text");
    document.getElementById("fileSource").classList.toggle("hidden", sourceMode !== "file");
}

async function analyzeDocument() {
    const fileInput = document.getElementById("documentFile");
    const documentInput = document.getElementById("document");
    const questionsInput = document.getElementById("questions");
    const analyzeButton = document.getElementById("analyzeButton");
    const analyzeError = document.getElementById("analyzeError");
    const analysisForm = document.getElementById("analysisForm");
    const analysisStatus = document.getElementById("analysisStatus");
    const result = document.getElementById("result");
    const resultText = document.getElementById("resultText");

    const sourceMode = document.querySelector('input[name="sourceMode"]:checked').value;
    analyzeError.innerText = "";
    if (sourceMode === "file" && !fileInput.files.length) {
        analyzeError.innerText = "Wybierz plik PDF.";
        return;
    }
    if (sourceMode === "text" && !documentInput.value.trim()) {
        analyzeError.innerText = "Wklej treść dokumentu.";
        return;
    }
    if (!questionsInput.value.trim()) {
        analyzeError.innerText = "Podaj przynajmniej jedno pytanie.";
        return;
    }

    result.classList.remove("hidden");
    resultText.innerText = "Analizowanie dokumentu...";
    analysisForm.classList.add("collapsed");
    analysisStatus.classList.remove("hidden");
    analysisStatus.innerText = "Trwa analiza dokumentu...";
    analyzeButton.disabled = true;

    const formData = new FormData();
    formData.append("questions", questionsInput.value);
    if (sourceMode === "file") {
        formData.append("file", fileInput.files[0]);
    } else {
        formData.append("document_text", documentInput.value);
    }

    try {
        const response = await fetch("/analyze", {
            method: "POST",
            body: formData
        });

        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.detail || "Analiza nie powiodła się.");
        }
        renderAnalysisResult(data.result);
        analysisStatus.innerText = "Analiza zakończona.";

    } catch (error) {
        result.classList.add("hidden");
        analysisForm.classList.remove("collapsed");
        analysisStatus.classList.add("hidden");
        analyzeError.innerText = error.message || "Wystąpił błąd podczas komunikacji z API.";
        console.error(error);
    } finally {
        analyzeButton.disabled = false;
    }
}

function renderAnalysisResult(result) {
    const resultText = document.getElementById("resultText");
    resultText.replaceChildren();

    if (!result || !Array.isArray(result.answers)) {
        resultText.innerText = JSON.stringify(result, null, 2);
        return;
    }

    result.answers.forEach((item) => {
        const answer = document.createElement("article");
        const question = document.createElement("h3");
        const response = document.createElement("p");
        question.innerText = item.question || "Pytanie";
        response.innerText = item.answer || "Brak odpowiedzi.";
        answer.append(question, response);
        resultText.append(answer);
    });
}
