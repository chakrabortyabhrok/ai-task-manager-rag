let p1 = new Promise((resolve, reject)=>{
    console.log('Promise is pending')
    setTimeout(()=>{
        console.log('I am a promise and I am fulfiled')
        resolve(true)
    }, 3000)
})


console.log(p1)


let p2 = new Promise((resolve, reject)=>{
    console.log('Promise is pending')
    setTimeout(()=>{
        console.log('I am a promise and I am rejected')
        reject(true)
    }, 3000)
})


p2.then((value) => {
    console.log(value)
},(error) => {
    console.log(typeof error)
})

p2.catch(() => {
    console.log('there is some error')
})
