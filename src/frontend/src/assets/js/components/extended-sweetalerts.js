/*
* Theme: Arclon - Responsive Bootstrap 5 Admin Dashboard
* Author: Coderthemes
* Component: Sweetalert init js
*/


const basicButton = document.getElementById('sweetalert-basic');
const titleButton = document.getElementById('sweetalert-title');
const longcontentButton = document.getElementById('sweetalert-longcontent');
const confirmButton = document.getElementById('sweetalert-confirm-button');
const paramsButton = document.getElementById('sweetalert-params');
const imageButton = document.getElementById('sweetalert-image');
const closeButton = document.getElementById('sweetalert-close');

const positionTopStart = document.querySelector('#position-top-start');
const positionTopEnd = document.querySelector('#position-top-end');
const positionBottomStart = document.querySelector('#position-bottom-start');
const positionBottomEnd = document.querySelector('#position-bottom-end');

const infoButton = document.getElementById('sweetalert-info');
const warningButton = document.getElementById('sweetalert-warning');
const errorButton = document.getElementById('sweetalert-error');
const successButton = document.getElementById('sweetalert-success');
const questionButton = document.getElementById('sweetalert-question');

// Click action handlers
infoButton.addEventListener('click', e => {

    Swal.fire({
        text: "Here's an example of an info SweetAlert!",
        icon: "info",
        buttonsStyling: false,
        confirmButtonText: "Ok, got it!",
        customClass: {
            confirmButton: "btn btn-info"
        }
    });
});

warningButton.addEventListener('click', e => {

    Swal.fire({
        text: "Here's an example of a warning SweetAlert!",
        icon: "warning",
        buttonsStyling: false,
        confirmButtonText: "Ok, got it!",
        customClass: {
            confirmButton: "btn btn-warning"
        }
    });
});

errorButton.addEventListener('click', e => {
    Swal.fire({
        text: "Here's an example of an error SweetAlert!",
        icon: "error",
        buttonsStyling: false,
        confirmButtonText: "Ok, got it!",
        customClass: {
            confirmButton: "btn btn-danger"
        }
    });
});

successButton.addEventListener('click', e => {
    Swal.fire({
        text: "Here's an example of a success SweetAlert!",
        icon: "success",
        buttonsStyling: false,
        confirmButtonText: "Ok, got it!",
        customClass: {
            confirmButton: "btn btn-success"
        }
    });
});

questionButton.addEventListener('click', e => {
    Swal.fire({
        text: "Here's an example of a question SweetAlert!",
        icon: "question",
        buttonsStyling: false,
        confirmButtonText: "Ok, got it!",
        customClass: {
            confirmButton: "btn btn-primary"
        }
    });
});


// Alerts Positions

// Top Start Alert
if (positionTopStart) {
    positionTopStart.onclick = function () {
        Swal.fire({
            position: 'top-start',
            icon: 'success',
            text: 'Your work has been saved',
            showConfirmButton: false,
            timer: 1500,
            customClass: {
                confirmButton: 'btn btn-primary'
            },
            buttonsStyling: false
        });
    };
}

// Top End Alert
if (positionTopEnd) {
    positionTopEnd.onclick = function () {
        Swal.fire({
            position: 'top-end',
            icon: 'success',
            text: 'Your work has been saved',
            showConfirmButton: false,
            timer: 1500,
            customClass: {
                confirmButton: 'btn btn-primary'
            },
            buttonsStyling: false
        });
    };
}

// Bottom Start Alert
if (positionBottomStart) {
    positionBottomStart.onclick = function () {
        Swal.fire({
            position: 'bottom-start',
            icon: 'success',
            text: 'Your work has been saved',
            showConfirmButton: false,
            timer: 1500,
            customClass: {
                confirmButton: 'btn btn-primary'
            },
            buttonsStyling: false
        });
    };
}

// Bottom End Alert
if (positionBottomEnd) {
    positionBottomEnd.onclick = function () {
        Swal.fire({
            position: 'bottom-end',
            icon: 'success',
            text: 'Your work has been saved',
            showConfirmButton: false,
            timer: 1500,
            customClass: {
                confirmButton: 'btn btn-primary'
            },
            buttonsStyling: false
        });
    };
}


// Basic
basicButton.addEventListener('click', e => {
    Swal.fire({
        title: 'Any fool can use a computer',
        customClass: {
            confirmButton: 'btn btn-primary mt-2',
        },
        buttonsStyling: false,
        // showCloseButton: true
    })
});

// A title with a text under
titleButton.addEventListener("click", function () {
    Swal.fire({
        title: "The Internet?",
        text: 'That thing is still around?',
        icon: 'question',
        customClass: {
            confirmButton: 'btn btn-primary mt-2',
        },
        buttonsStyling: false,
        showCloseButton: true
    })
});

// Success Message
successButton.addEventListener("click", function () {
    Swal.fire({
        title: 'Good job!',
        text: 'You clicked the button!',
        icon: 'success',
        showCancelButton: true,
        customClass: {
            confirmButton: 'btn btn-primary me-2 mt-2',
            cancelButton: 'btn btn-danger mt-2',
        },
        buttonsStyling: false,
        showCloseButton: true
    })
});

// error Message
errorButton.addEventListener("click", function () {
    Swal.fire({
        title: 'Oops...',
        text: 'Something went wrong!',
        icon: 'error',
        customClass: {
            confirmButton: 'btn btn-primary mt-2',
        },
        buttonsStyling: false,
        footer: '<a href="#!">Why do I have this issue?</a>',
        showCloseButton: true
    })
});

//  long content
longcontentButton.addEventListener("click", function () {
    Swal.fire({
        imageUrl: 'https://placeholder.pics/svg/300x1500',
        imageHeight: 1500,
        imageAlt: 'A tall image',
        customClass: {
            confirmButton: 'btn btn-primary mt-2',
        },
        buttonsStyling: false,
        showCloseButton: true
    })
});

// Warning Message
confirmButton.addEventListener("click", function () {
    Swal.fire({
        title: "Are you sure?",
        text: "You won't be able to revert this!",
        icon: "warning",
        showCancelButton: true,
        customClass: {
            confirmButton: 'btn btn-primary me-2 mt-2',
            cancelButton: 'btn btn-danger mt-2',
        },
        confirmButtonText: "Yes, delete it!",
        buttonsStyling: false,
        showCloseButton: true
    }).then(function (result) {
        if (result.value) {
            Swal.fire({
                title: 'Deleted!',
                text: 'Your file has been deleted.',
                icon: 'success',
                customClass: {
                    confirmButton: 'btn btn-primary mt-2',
                },
                buttonsStyling: false
            })
        }
    });
});

// Parameter
paramsButton.addEventListener("click", function () {
    Swal.fire({
        title: 'Are you sure?',
        text: "You won't be able to revert this!",
        icon: 'warning',
        showCancelButton: true,
        confirmButtonText: 'Yes, delete it!',
        cancelButtonText: 'No, cancel!',
        customClass: {
            confirmButton: 'btn btn-primary me-2 mt-2',
            cancelButton: 'btn btn-danger mt-2',
        },
        buttonsStyling: false,
        showCloseButton: true
    }).then(function (result) {
        if (result.value) {
            Swal.fire({
                title: 'Deleted!',
                text: 'Your file has been deleted.',
                icon: 'success',
                customClass: {
                    confirmButton: 'btn btn-primary mt-2',
                },
                buttonsStyling: false
            })
        } else if (
            // Read more about handling dismissals
            result.dismiss === Swal.DismissReason.cancel
        ) {
            Swal.fire({
                title: 'Cancelled',
                text: 'Your imaginary file is safe :)',
                icon: 'error',
                customClass: {
                    confirmButton: 'btn btn-primary mt-2',
                },
                buttonsStyling: false
            })
        }
    });
});


// Custom Image
imageButton.addEventListener("click", function () {
    Swal.fire({
        title: 'Sweet!',
        text: 'Modal with a custom image.',
        imageUrl: 'assets/images/logo-sm.png',
        imageHeight: 40,
        customClass: {
            confirmButton: 'btn btn-primary mt-2',
        },
        buttonsStyling: false,
        // animation: false,
        showCloseButton: true
    })
});

// Auto Close Timer
closeButton.addEventListener("click", function () {
    var timerInterval;
    Swal.fire({
        title: 'Auto close alert!',
        html: 'I will close in <strong></strong> seconds.',
        timer: 2000,
        timerProgressBar: true,
        showCloseButton: true,
        didOpen: function () {
            Swal.showLoading()
            timerInterval = setInterval(function () {
                var content = Swal.getHtmlContainer()
                if (content) {
                    var b = content.querySelector('b')
                    if (b) {
                        b.textContent = Swal.getTimerLeft()
                    }
                }
            }, 100)
        },
        onClose: function () {
            clearInterval(timerInterval)
        }
    }).then(function (result) {
        /* Read more about handling dismissals below */
        if (result.dismiss === Swal.DismissReason.timer) {
            console.log('I was closed by the timer')
        }
    })
});


// custom html alert
document.getElementById("custom-html-alert").addEventListener("click", function () {
    Swal.fire({
        title: '<i>HTML</i> <u>example</u>',
        icon: 'info',
        html: 'You can use <b>bold text</b>, ' +
            '<a href="#">links</a> ' +
            'and other HTML tags',
        showCloseButton: true,
        showCancelButton: true,
        customClass: {
            confirmButton: 'btn btn-success me-2',
            cancelButton: 'btn btn-danger',
        },
        buttonsStyling: false,
        confirmButtonText: '<i class="ti ti-thumb-up-filled me-1"></i> Great!',
        cancelButtonText: '<i class="ti ti-thumb-down-filled"></i>',
        showCloseButton: true
    })
});

// Custom width padding
document.getElementById("custom-padding-width-alert").addEventListener("click", function () {
    Swal.fire({
        title: 'Custom width, padding, background.',
        width: 600,
        padding: 100,
        customClass: {
            confirmButton: 'btn btn-primary',
        },
        buttonsStyling: false,
        background: 'var(--ct-secondary-bg) url(assets/images/small/small-5.jpg) no-repeat center'
    })
});

// Ajax
document.getElementById("ajax-alert").addEventListener("click", function () {
    Swal.fire({
        title: 'Submit email to run ajax request',
        input: 'email',
        showCancelButton: true,
        confirmButtonText: 'Submit',
        showLoaderOnConfirm: true,
        customClass: {
            confirmButton: 'btn btn-primary me-2',
            cancelButton: 'btn btn-danger',
        },
        buttonsStyling: false,
        showCloseButton: true,
        preConfirm: function (email) {
            return new Promise(function (resolve, reject) {
                setTimeout(function () {
                    if (email === 'taken@example.com') {
                        reject('This email is already taken.')
                    } else {
                        resolve()
                    }
                }, 2000)
            })
        },
        allowOutsideClick: false
    }).then(function (email) {
        Swal.fire({
            icon: 'success',
            title: 'Ajax request finished!',
            customClass: {
                confirmButton: 'btn btn-primary',
            },
            buttonsStyling: false,
            html: 'Submitted email: ' + email
        })
    })
});