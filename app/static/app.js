async function analyzeDocument() {

    const documentText = document.getElementById("document").value;
    const result = document.getElementById("result");
    const resultText = document.getElementById("resultText");

    if (!documentText.trim()) {
        alert("Wklej najpierw dokument.");
        return;
    }

    result.classList.remove("hidden");

    resultText.innerText = "Analizowanie dokumentu...";

    try {

        const response = await fetch("/api/analyze", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                text: documentText
            })
        });

        const data = await response.json();

        resultText.innerText = data.message;

    } catch (error) {

        resultText.innerText =
            "Wystąpił błąd podczas komunikacji z API.";

        console.error(error);
    }
}
