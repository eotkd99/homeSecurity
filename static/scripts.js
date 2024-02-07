document.addEventListener('DOMContentLoaded', function () {
    // 화재 경고 배너 표시 여부를 제어하기 위한 변수
    var fireAlertVisible = false;
    // 화재 감지 기준 온도 (섭씨)
    var fireDetectionTemperature = 20;

    // 온도 그래프
    var temperatureChart = new Chart(document.getElementById('temperatureChart'), {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: 'Temperature',
                data: [],
                borderColor: 'rgb(255, 99, 132)',
                borderWidth: 1,
                fill: false
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true, // 세로 크기 고정
            scales: {
                y: {
                    beginAtZero: true,
                    suggestedMax: 40
                }
            }
        }
    });

    // 습도 그래프
    var humidityChart = new Chart(document.getElementById('humidityChart'), {
        type: 'line',
        data: {
            labels: [],
            datasets: [{
                label: 'Humidity',
                data: [],
                borderColor: 'rgb(54, 162, 235)',
                borderWidth: 1,
                fill: false
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true, // 세로 크기 고정
            scales: {
                y: {
                    beginAtZero: true,
                    suggestedMax: 100
                }
            }
        }
    });

    // 주기적으로 온도와 습도 데이터를 가져와 그래프를 업데이트하는 함수
    function updateCharts() {
        fetch('/api/data')
            .then(response => {
                if (!response.ok) {
                    throw new Error('Server Error');
                }
                return response.json();
            })
            .then(data => {
                // 온도 업데이트
                let currentTemperature = data.temperature[data.temperature.length - 1];
                document.getElementById('currentTemperature').textContent = currentTemperature + '°C';

                // 습도 업데이트
                let currentHumidity = data.humidity[data.humidity.length - 1];
                document.getElementById('currentHumidity').textContent = currentHumidity + '%';

                // 그래프 업데이트
                temperatureChart.data.labels = data.temperature.map((_, index) => index + 1);
                temperatureChart.data.datasets[0].data = data.temperature;
                temperatureChart.update();

                humidityChart.data.labels = data.humidity.map((_, index) => index + 1);
                humidityChart.data.datasets[0].data = data.humidity;
                humidityChart.update();

                // 화재 감지 여부 확인 및 경고 배너 표시
                if (currentTemperature > fireDetectionTemperature && !fireAlertVisible) {
                    document.getElementById('fireAlert').style.display = 'block';
                    fireAlertVisible = true;
                } else if (currentTemperature <= fireDetectionTemperature && fireAlertVisible) {
                    document.getElementById('fireAlert').style.display = 'none';
                    fireAlertVisible = false;
                }
            })
            .catch(error => {
                console.error('Error:', error);
            });

    }

    // 5초마다 그래프를 업데이트
    setInterval(updateCharts, 5000);

    // 최초 로딩 시 그래프 업데이트
    updateCharts();
});
