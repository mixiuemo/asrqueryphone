import { message } from 'antd'

let net = {
    // 网络提示状态
    state: true,
    load: function (url, callback, errCallback) {
        fetch(url, {
            method: "GET",
            headers: {
                'Accept': 'application/json; charset=utf-8',
                'Content-Type': 'application/json; charset=utf-8',
                'x-access-token': window.token,
            }
        }).then(function (response) {
            return response.json()
        }).then(function (ret) {
            let list = ret;
            if (ret.list) {
                list = ret.list;
            }
            list.forEach(function (item) {
                if (item.objectId) {
                    item.id = item.objectId;
                }
            });
            callback(ret);
        }).catch(function (error) {
            if (errCallback) {
                errCallback(error);
            }
            console.log(error);
        }).done();
    },
    loadZip: function (url, callback, errCallback) {
        fetch(url, {
            method: "GET",
            headers: {
                'Accept-Encoding': 'gzip',
                'Content-Type': 'application/json; charset=utf-8',
                'x-access-token': window.token,
            }
        }).then(function (response) {
            return response.json()
        }).then(function (ret) {
            let list = ret;
            if (ret.list) {
                list = ret.list;
            }
            list.forEach(function (item) {
                if (item.objectId)
                    item.id = item.objectId;
            });
            callback(ret);
        }).catch(function (error) {
            if (errCallback) {
                errCallback(error);
            }
            console.log(error);
        }).done();
    },
    loadOne: function (url, callback, errCallback) {
        fetch(url, {
            method: "GET",
            headers: {
                'Accept': 'application/json; charset=utf-8',
                'Content-Type': 'application/json; charset=utf-8',
                'x-access-token': window.token,
            }
        }).then(function (response) {
            return response.json()
        }).then(function (data) {
            callback(data);
        }).catch(function (error) {
            console.log(error);
            if (errCallback) {
                errCallback(error);
            }
        }).done();
    },
    get: function (url, callback, errorCallback) {
        fetch(url, {
            // headers: {
            //   'x-access-token': global.token,
            // }
        }).then(function (response) {
            return response.json()
        }).then(function (data) {
            callback(data);
        }).catch(function (error) {
            console.log(error);
            if (errorCallback) {
                errorCallback(error);
            }
        });
    },
    delete: function (url, callback, errorCallback) {
        fetch(url, {
            method: "DELETE",
            // headers: {
            //   'x-access-token': global.token,
            // }
        }).then(function (response) {
            return response.json()
        }).then(function (data) {
            callback(data);
        }).catch(function (error) {
            if (errorCallback) {
                errorCallback(error);
            }
        });
    },
    put: function (url, obj, callback, errCallback) {
        // let headers = new Headers();
        // if(global.loginUser)
        //   headers.append("X-API-TOKEN", global.loginUser.token);
        fetch(url, {
            method: "PUT",
            headers: {
                'x-access-token': window.token,
            },
            body: JSON.stringify(obj)
        }).then(function (response) {
            return response.json()
        }).then(function (data) {
            callback(data);
        }).catch(function (error) {
            console.log(error);
            if (errCallback) {
                errCallback(error);
            }
        });
    },
    post: function (url, data, callback, errCallback) {
        // console.log("net post", url);

        if (this.state) {
            this.state = false

            // 当网速小于 140k/s 提示网速慢
            if (window.navigator && window.navigator.connection && window.navigator.connection.downlink * 1024 / 8 < 140) {
                //message.warning('当前网络状态不佳！')
            }

            // 5s 内不再提示
            setTimeout(() => {
                this.state = true
            }, 5000)
        }

        // let headers = new Headers();
        // if(global.loginUser)
        //   headers.append("X-API-TOKEN", global.loginUser.token);
        fetch(url, {
            method: "POST",
            headers: {
                'x-access-token': window.token,
            },
            body: JSON.stringify(data)
        }).then(function (response) {
            return response.json()
        }).then(function (data) {
            callback(data);
        }).catch(function (error) {
            console.log(error);
            if (errCallback) {
                errCallback(error);
            }
        });
    },
    upload: function (url, formData, callback, errCallback, name) {
        let n = name;
        if (formData.get) {
            n = formData.get('name');
        }
        fetch(url, {
            method: "POST",
            headers: {
                // "Raw-Name":n,
                'x-access-token': window.token,
            },
            body: formData
        }).then(function (response) {
            return response.json()
        }).then(function (data) {
            callback(data);
        }).catch(function (error) {
            console.log(error);
            if (errCallback) {
                errCallback(error);
            }
        });
    },
    // exportFile:function(url,query,file) {
    //     var xhttp = new XMLHttpRequest();
    //     xhttp.onreadystatechange = function() {
    //         var a;
    //         if (xhttp.readyState === 4 && xhttp.status === 200) {
    //             // Trick for making downloadable link
    //             a = document.createElement('a');
    //             a.href = window.URL.createObjectURL(xhttp.response);
    //             // Give filename you wish to download
    //             a.download = file;
    //             a.style.display = 'none';
    //             document.body.appendChild(a);
    //             a.click();
    //         }
    //     };
    //     // Post data to URL which handles post request
    //     xhttp.open("POST", url);
    //     xhttp.setRequestHeader("Content-Type", "application/json");
    //     // You should set responseType as blob for binary responses
    //     xhttp.responseType = 'blob';
    //     xhttp.send(JSON.stringify(query));
    // },
    exportFile: function (url, query, file) {
        var xhttp = new XMLHttpRequest();
        xhttp.onreadystatechange = function () {
            var a;
            if (xhttp.readyState === 4 && xhttp.status === 200) {
                // Trick for making downloadable link
                a = document.createElement('a');
                a.href = window.URL.createObjectURL(xhttp.response);
                // Give filename you wish to download
                a.download = file;
                a.style.display = 'none';
                document.body.appendChild(a);
                a.click();
            }
        };
        // Post data to URL which handles post request
        xhttp.open("GET", url);
        xhttp.setRequestHeader("Content-Type", "application/json");
        // You should set responseType as blob for binary responses
        xhttp.responseType = 'blob';
        xhttp.send();
    },
    downloadExcel: function (url, file) {
        var xhttp = new XMLHttpRequest();
        xhttp.onreadystatechange = function () {
            var a;
            if (xhttp.readyState === 4 && xhttp.status === 200) {
                // Trick for making downloadable link
                a = document.createElement("a");
                a.href = window.URL.createObjectURL(xhttp.response);
                // Give filename you wish to download
                a.download = file;
                a.style.display = "none";
                document.body.appendChild(a);
                a.click();
            }
        };
        // Post data to URL which handles post request
        xhttp.open("GET", url);
        xhttp.setRequestHeader("Content-Type", "application/json");
        // You should set responseType as blob for binary responses
        xhttp.responseType = "blob";
        xhttp.send();
    },
    downloadExcelByFilter: function (url, query, file) {
        var xhttp = new XMLHttpRequest();
        xhttp.onreadystatechange = function () {
            var a;
            if (xhttp.readyState === 4 && xhttp.status === 200) {
                // Trick for making downloadable link
                a = document.createElement("a");
                a.href = window.URL.createObjectURL(xhttp.response);
                // Give filename you wish to download
                a.download = file;
                a.style.display = "none";
                document.body.appendChild(a);
                a.click();
            }
        };
        // Post data to URL which handles post request
        xhttp.open("POST", url);
        xhttp.setRequestHeader("Content-Type", "application/json;charset=utf-8");
        // You should set responseType as blob for binary responses
        xhttp.responseType = "blob";
        xhttp.send(query);
        // xhttp.send(JSON.stringify(query));
    },
    downloadExcelByFilterText: function (url, query, file) {
        var xhttp = new XMLHttpRequest();
        xhttp.onreadystatechange = function () {
            var a;
            if (xhttp.readyState === 4 && xhttp.status === 200) {
                // Trick for making downloadable link
                a = document.createElement("a");
                a.href = window.URL.createObjectURL(xhttp.response);
                // Give filename you wish to download
                a.download = file;
                a.style.display = "none";
                document.body.appendChild(a);
                a.click();
            }
        };
        // Post data to URL which handles post request
        xhttp.open("POST", url);
        xhttp.setRequestHeader("Content-Type", "text/plain");
        // You should set responseType as blob for binary responses
        xhttp.responseType = "blob";
        xhttp.send(JSON.stringify(query));
    },
    downloadExcelByStandard: function (url, file) {
        console.log('downloadExcelByStandard', url);
        var xhttp = new XMLHttpRequest();
        xhttp.onreadystatechange = function () {
            var a;
            if (xhttp.readyState === 4 && xhttp.status === 200) {
                // Trick for making downloadable link
                a = document.createElement("a");
                a.href = window.URL.createObjectURL(xhttp.response);
                // Give filename you wish to download
                a.download = file;
                a.style.display = "none";
                document.body.appendChild(a);
                a.click();
            }
        };
        // Post data to URL which handles post request
        xhttp.open("GET", url);
        xhttp.setRequestHeader("Content-Type", "application/json");
        // You should set responseType as blob for binary responses
        xhttp.responseType = "blob";
        xhttp.send(JSON.stringify({}));
    },
    downloadText: function (url, file) {
        console.log('downloadText', url);
        var xhttp = new XMLHttpRequest();
        xhttp.onreadystatechange = function () {
            var a;
            if (xhttp.readyState === 4 && xhttp.status === 200) {
                // Trick for making downloadable link
                a = document.createElement("a");
                a.href = window.URL.createObjectURL(xhttp.response);
                // Give filename you wish to download
                a.download = file;
                a.style.display = "none";
                document.body.appendChild(a);
                a.click();
            }
        };
        // Post data to URL which handles post request
        xhttp.open("GET", url);
        xhttp.setRequestHeader("Content-Type", "application/json");
        // You should set responseType as blob for binary responses
        xhttp.responseType = "blob";
        xhttp.send();
    }
};

export default net; 
