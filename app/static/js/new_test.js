document.addEventListener("DOMContentLoaded", () => {
  const sliderWrapper = document.querySelector(".symptom-slider-wrapper")
  if (!sliderWrapper) return // Only run if the slider exists on the page

  const slides = document.querySelectorAll(".symptom-slide")
  let currentSlide = 0

  // Use event delegation for the 'Next' buttons
  sliderWrapper.addEventListener("click", (e) => {
    // Check if a 'next-btn' was clicked
    if (e.target && e.target.classList.contains("next-btn")) {
      const currentSlideElement = slides[currentSlide]
      const radios = currentSlideElement.querySelectorAll('input[type="radio"]')

      // Validate that an option was selected before proceeding
      if (radios.length > 0 && !Array.from(radios).some((r) => r.checked)) {
        alert("Please select an option to continue.")
        return // Stop if nothing is selected
      }

      // Move to the next slide
      currentSlide++
      if (currentSlide < slides.length) {
        sliderWrapper.style.transform = `translateX(-${currentSlide * 25}%)`
      }
    }
  })
})
