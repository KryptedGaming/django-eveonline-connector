console.log('hi')

function setModalID (external_id) {
    console.log("Modal ID: " + external_id)
    id = document.getElementById('entityModalID')
    id.innerHTML = external_id
}

function hideModalActions () {
    name = document.getElementById('entityModalName')
    profilePicture = document.getElementById('entityModalProfilePicture')
    detailName = document.getElementById('entityModalDetailName')
    affiliation = document.getElementById('entityModalAffiliation')
    links = document.getElementById('entityModalLinks')

    name.innerHTML = '<i class="fa fa-spinner fa-spin"></i>'
    profilePicture.innerHTML = '<i style="font-size: 128px" class="fa fa-spinner fa-spin"></i>'
    detailName.innerHTML = '<i class="fa fa-spinner fa-spin"></i>'
    affiliation.innerHTML = '<i class="fa fa-spinner fa-spin"></i>'
    links.innerHTML = '<i class="fa fa-spinner fa-spin"></i>'
}

async function loadModal() {
    id = document.getElementById('entityModalID')
    name = document.getElementById('entityModalName')
    profilePicture = document.getElementById('entityModalProfilePicture')
    detailName = document.getElementById('entityModalDetailName')
    affiliation = document.getElementById('entityModalAffiliation')
    links = document.getElementById('entityModalLinks')
    response = await fetch('/eveonline/api/entity/resolve?external_id=' + id.innerHTML)
    response = await response.json()

    if (response.type == "character")
        profilePicture.innerHTML = `<img class="profile-user-img img-responsive img-circle" src="https://imageserver.eveonline.com/Character/${response.external_id}_128.jpg" alt="User profile picture">`
    else if (response.type == "corporation")
        profilePicture.innerHTML = `<img class="profile-user-img img-responsive img-circle" src="https://imageserver.eveonline.com/Corporation/${response.external_id}_128.png" alt="User profile picture">`
    else if (response.type == "alliance")
        profilePicture.innerHTML = `<img class="profile-user-img img-responsive img-circle" src="https://imageserver.eveonline.com/Alliance/${response.external_id}_128.png" alt="User profile picture">`
    detailName.innerHTML = response.name 
    affiliation.innerHTML = "Not Implemented"
    links.innerHTML = `
    <a href="http://evewho.com/${response.type}/${response.external_id}" target="_blank">
        <img src="/static/django_eveonline_connector/img/evewho_logo.ico" width="16x">
    </a>
    <a href="https://zkillboard.com/${response.type}/${response.external_id}" target="_blank">
        <img src="/static/django_eveonline_connector/img/zkillboard_logo.ico" width="16x">
    </a>
    `
}

$('#entityModal').on('hidden.bs.modal', function () {
    hideModalActions()
})

$('#entityModal').on('shown.bs.modal', function (e) {
    loadModal()
})