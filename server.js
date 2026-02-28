const express = require('express')
const mongoose = require('mongoose')
const path = require('path')
const port =3000


app.get('/',(req,res)=>{
    res.sendFile(path.join(__dirname,'login.html'))
})

const app=express()
app.listen(port,()=>{
    console.log("Server started")
})

    