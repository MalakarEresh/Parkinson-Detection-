document.addEventListener("DOMContentLoaded", function () {
  // Check if the chart canvas and the global data variables (created in dashboard.html) exist
  if (
    document.getElementById("myPieChart") &&
    typeof chartLabels !== "undefined" &&
    typeof chartData !== "undefined"
  ) {
    const ctx = document.getElementById("myPieChart")

    new Chart(ctx, {
      type: "doughnut",
      data: {
        labels: chartLabels, // Use the global variable
        datasets: [
          {
            data: chartData, // Use the global variable
            backgroundColor: [
              "#4e73df",
              "#1cc88a",
              "#f6c23e",
              "#e74a3b",
              "#5a5c69",
              "#36b9cc",
            ],
            hoverBackgroundColor: [
              "#2e59d9",
              "#17a673",
              "#dda20a",
              " #c73021",
              "#404148",
              "#2c9faf",
            ],
            hoverBorderColor: "rgba(234, 236, 244, 1)",
          },
        ],
      },
      options: {
        maintainAspectRatio: false,
        plugins: {
          legend: {
            display: false, // We use our own custom legend in the HTML
          },
          tooltip: {
            backgroundColor: "rgb(255,255,255)",
            bodyColor: "#858796",
            borderColor: "#dddfeb",
            borderWidth: 1,
            padding: 15,
            displayColors: false,
            caretPadding: 10,
          },
        },
        cutout: "80%", // For Chart.js v3+
      },
    })
  }
})
