package routers

import (
	"beegoserver/controllers"
	bee
	go "github.com/beego/beego/v2/server/web"
)

func init() {
    beego.Router("/", &controllers.MainController{})
	beego.Router("/verify", &controllers.CaController{})
}
