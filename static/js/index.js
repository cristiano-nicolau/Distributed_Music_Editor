


//variables
const item1 = document.getElementById('item1');
const fileDropArea = document.getElementById('file-drop');
const fileInput = fileDropArea.querySelector('.file-input');
const item2 = document.getElementById('item2');
const musicDetailsContainer = document.getElementById('music-details-container');
const item3 = document.getElementById('item3');
const musicTableContainer = document.getElementById('list-music');
const item4 = document.getElementById('item4');
const processMusicContainer = document.getElementById('process-music');

// File Upload
fileDropArea.style.display = 'none';
musicDetailsContainer.style.display = 'none';
musicTableContainer.style.display = 'none';
processMusicContainer.style.display = 'none';

const coursesItem = document.getElementById('item1');

item1.addEventListener('click', function () {
  if (fileDropArea.style.display === 'none') {
    fileDropArea.style.display = 'block';
    musicDetailsContainer.style.display = 'none';
    musicTableContainer.style.display = 'none';
    processMusicContainer.style.display = 'none';

  } else {
    fileDropArea.style.display = 'none';
  }
});

item2.addEventListener('click', function () {
  if (musicDetailsContainer.style.display === 'none') {
    musicDetailsContainer.style.display = 'block';
    fileDropArea.style.display = 'none';
    musicTableContainer.style.display = 'none';
    processMusicContainer.style.display = 'none';
  } else {
    musicDetailsContainer.style.display = 'none';
  }
});

item3.addEventListener('click', function () {
  // Toggle the visibility of the music table container
  if (musicTableContainer.style.display === 'none') {
    musicTableContainer.style.display = 'block';
    musicDetailsContainer.style.display = 'none';
    fileDropArea.style.display = 'none';
    processMusicContainer.style.display = 'none';
    fetchMusicData();
  } else {
    musicTableContainer.style.display = 'none';
  }
});

item4.addEventListener('click', function () {
  // Toggle the visibility of the music table container
  if (processMusicContainer.style.display === 'none') {
    processMusicContainer.style.display = 'block';
    musicDetailsContainer.style.display = 'none';
    fileDropArea.style.display = 'none';
    musicTableContainer.style.display = 'none';
  } else {
    processMusicContainer.style.display = 'none';
  }
});

fileInput.addEventListener('change', function () {
  const files = fileInput.files;
  if (files.length > 0) {
    console.log('Files selected:', files);
    // Perform any other actions with the selected files
  }
});

const submitButton = document.getElementById('submit-btn');

// Add an event listener to the submit button
submitButton.addEventListener('click', (event) => {
  event.preventDefault(); // Prevent the default form submission

  // Check if a file is selected
  if (fileInput.files.length > 0) {
    const file = fileInput.files[0];

    // Create a FormData object and append the file to it
    const formData = new FormData();
    formData.append('file', file);

    // Send a POST request to the server with the file data
    fetch('/music', {
      method: 'POST',
      body: formData
    })
      .then(response => response.json())
      .then(data => {
        // Handle the response from the server
        console.log(data);
        // You can perform any further actions here, such as displaying the response data on the page
      })
      .catch(error => {
        // Handle any errors that occur during the request
        console.error(error);
      });
  }
});



// Music Details


document.getElementById("submit-btn2").addEventListener("click", function() {
  var musicId = document.getElementById("music-id-input").value;
  fetch("/music/" + musicId)
      .then(function(response) {
          return response.json();
      })
      .then(function(data) {
          if (data.error) {
              // Handle the error case
              var responseContainer = document.getElementById("response-container");
              responseContainer.innerHTML = "Error: " + data.error;
          } else {
              // Handle the success case
              var responseContainer = document.getElementById("response-container");
              responseContainer.innerHTML = "Progress: " + data.progress + "%";
              responseContainer.innerHTML += "<br>Instruments: " + data.instruments;
              responseContainer.innerHTML += "<br>Final: " + data.final;
          }
      })
      .catch(function(error) {
          console.log("Error: " + error);
      });
});


// listar as musicas todas




function fetchMusicData() {
  fetch('/music')
    .then(response => response.json())
    .then(data => {
      // Clear the table body
      const tableBody = document.getElementById('music-table-body');
      tableBody.innerHTML = '';

      // Iterate over the music data and create table rows
      data.forEach(music => {
        const row = document.createElement('tr');
        row.innerHTML = `
          <td style="width:10%">${music.music_id}</td>
          <td style="width:23.33%">${music.name}</td>
          <td style="width:23.33%">${music.band}</td>
          <td style="width:23.33%">
            <ul>
              ${music.tracks.map(track => `<li>${track.name} (ID: ${track.track_id})</li>`).join('')}
            </ul>
          </td>
                `;
        tableBody.appendChild(row);
      });
    })
    .catch(error => console.error('Error:', error));
}




/* process music */


document.getElementById("process-btn").addEventListener("click", function() {
  var musicId = document.getElementById("music-id-input").value;
  console.log("Music ID:", musicId);
  
  var instruments = [
      document.getElementById("process-track-id1").value,
      document.getElementById("process-track-id2").value,
      document.getElementById("process-track-id3").value,
      document.getElementById("process-track-id4").value
  ];
  console.log("Instruments:", instruments);
  
  fetch("/music/" + musicId, {
      method: "POST",
      headers: {
          "Content-Type": "application/json"
      },
      body: JSON.stringify({
          instruments: instruments
      })
  })
  .then(function(response) {
      return response.json();
  })
  .then(function(data) {
      // Display the response data on the HTML page
      var responseContainer = document.getElementById("response-container");
      responseContainer.innerHTML = "Success: " + data.Sucesso;
  })
  .catch(function(error) {
      console.log("Error: " + error);
  });
});
