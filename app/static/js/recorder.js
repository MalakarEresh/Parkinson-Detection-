document.addEventListener("DOMContentLoaded", () => {
  // Find the form on the current page. It could be on dashboard.html or audio_test.html
  const form =
    document.getElementById("audio-form") ||
    document.getElementById("report-form")
  if (!form) return // Exit if no form is found

  const submitButton = document.getElementById("submitButton")
  const audioUpload = document.getElementById("audioUpload")
  const recordButton = document.getElementById("recordButton")
  const stopButton = document.getElementById("stopButton")
  const audioPlayback = document.getElementById("audioPlayback")
  const recordingStatus = document.getElementById("recording-status")
  const submitStatus = document.getElementById("submit-status")

  let mediaRecorder
  let audioChunks = []
  let recordedBlob = null

  function checkCanSubmit() {
    const hasRecordedAudio = recordedBlob !== null
    const hasUploadedAudio = audioUpload && audioUpload.files.length > 0

    if (submitButton) {
      submitButton.disabled = !(hasRecordedAudio || hasUploadedAudio)
    }
    if (submitStatus) {
      submitStatus.textContent =
        hasRecordedAudio || hasUploadedAudio
          ? ""
          : "Please record or upload an audio file to submit."
    }
  }

  if (recordButton) {
    recordButton.addEventListener("click", async (event) => {
      event.preventDefault()
      if (audioUpload) {
        audioUpload.value = ""
        audioUpload.disabled = true
      }
      recordedBlob = null
      audioPlayback.classList.add("d-none")
      try {
        const constraints = {
          audio: {
            autoGainControl: false,
            echoCancellation: false,
            noiseSuppression: false,
          },
        }
        const stream = await navigator.mediaDevices.getUserMedia(constraints)
        mediaRecorder = new MediaRecorder(stream)
        audioChunks = []
        mediaRecorder.ondataavailable = (e) => audioChunks.push(e.data)
        mediaRecorder.onstop = () => {
          recordedBlob = new Blob(audioChunks, { type: "audio/webm" })
          audioPlayback.src = URL.createObjectURL(recordedBlob)
          audioPlayback.classList.remove("d-none")
          recordingStatus.textContent =
            "Recording finished. Ready for submission."
          checkCanSubmit()
        }
        mediaRecorder.start()
        recordButton.disabled = true
        stopButton.disabled = false
        recordingStatus.textContent = "Recording..."
      } catch (err) {
        recordingStatus.textContent = "Error: Could not access microphone."
        if (audioUpload) audioUpload.disabled = false
      }
    })
  }

  if (stopButton) {
    stopButton.addEventListener("click", (event) => {
      event.preventDefault()
      if (mediaRecorder?.state === "recording") mediaRecorder.stop()
      recordButton.disabled = false
      stopButton.disabled = true
    })
  }

  if (audioUpload) {
    audioUpload.addEventListener("change", () => {
      if (audioUpload.files.length > 0) {
        if (recordButton) recordButton.disabled = true
        if (stopButton) stopButton.disabled = true
        recordedBlob = null
        if (audioPlayback) audioPlayback.classList.add("d-none")
        if (recordingStatus)
          recordingStatus.textContent = "File selected. Ready to submit."
      } else {
        if (recordButton) recordButton.disabled = false
      }
      checkCanSubmit()
    })
  }

  form.addEventListener("submit", (event) => {
    event.preventDefault() // ALWAYS prevent the default submission

    submitButton.disabled = true
    submitButton.textContent = "Submitting..."

    // Manually build FormData to guarantee correctness
    const formData = new FormData(form)

    // This check is crucial. We must ensure only ONE audio source is in the FormData.
    if (recordedBlob) {
      // If a recording exists, it takes precedence.
      formData.delete("uploaded_audio_data") // Remove any selected file
      formData.append("recorded_audio_data", recordedBlob, "recording.webm")
    } else if (audioUpload && audioUpload.files.length > 0) {
      // The uploaded file is already in formData from the constructor, so we do nothing.
    } else {
      // This case should be prevented by the disabled submit button, but as a fallback:
      flash("No audio file was provided.", "danger") // This is a client-side alert
      submitButton.disabled = false
      submitButton.textContent = "Analyze & Complete Test"
      return
    }

    fetch(form.action, {
      method: "POST",
      body: formData,
    })
      .then((response) => {
        if (response.redirected) {
          window.location.href = response.url
        } else {
          // If not redirected, the server might have sent an error.
          // Reloading is the simplest way to see the flash message.
          window.location.reload()
        }
      })
      .catch((error) => {
        console.error("Submission Error:", error)
        submitButton.disabled = false
        submitButton.textContent = "Analyze & Complete Test"
        if (submitStatus) submitStatus.textContent = "A network error occurred."
      })
  })

  // Initial check when the page loads
  checkCanSubmit()
})
