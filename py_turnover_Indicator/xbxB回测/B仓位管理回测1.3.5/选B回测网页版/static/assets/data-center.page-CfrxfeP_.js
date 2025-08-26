import{I as U,J as ne,c as p,o as l,e as d,b as k,K as P,m as I,k as T,L as u,t as w,g as C,H as y,M as A,w as g,v as me,N as q,O as ie,P as R,Q as fe,S as O,F,f as se,U as pe,V as he,W as B,X as re,Y as G,Z as Y,_ as be,$ as ge,a0 as Ie,a1 as Z,a2 as $,a3 as ve,a4 as K,a5 as j,a6 as ye,a7 as J,a as ke,h as we,r as z,i as xe,A as Le,p as x,l as L,T as Pe}from"./index-wXo1eE9t.js";import{s as Se,a as Me,b as Ke,c as Ce,g as De,d as Ee,e as Be,f as Te,h as Oe,i as Ae,j as E,k as Q}from"./service.provider-DG1JL4g4.js";import{O as Fe,s as Ve,a as _e,g as X,b as ze}from"./index-CW_Bg6A1.js";var je=`
    .p-fieldset {
        background: dt('fieldset.background');
        border: 1px solid dt('fieldset.border.color');
        border-radius: dt('fieldset.border.radius');
        color: dt('fieldset.color');
        padding: dt('fieldset.padding');
        margin: 0;
    }

    .p-fieldset-legend {
        background: dt('fieldset.legend.background');
        border-radius: dt('fieldset.legend.border.radius');
        border-width: dt('fieldset.legend.border.width');
        border-style: solid;
        border-color: dt('fieldset.legend.border.color');
        padding: dt('fieldset.legend.padding');
        transition:
            background dt('fieldset.transition.duration'),
            color dt('fieldset.transition.duration'),
            outline-color dt('fieldset.transition.duration'),
            box-shadow dt('fieldset.transition.duration');
    }

    .p-fieldset-toggleable > .p-fieldset-legend {
        padding: 0;
    }

    .p-fieldset-toggle-button {
        cursor: pointer;
        user-select: none;
        overflow: hidden;
        position: relative;
        text-decoration: none;
        display: flex;
        gap: dt('fieldset.legend.gap');
        align-items: center;
        justify-content: center;
        padding: dt('fieldset.legend.padding');
        background: transparent;
        border: 0 none;
        border-radius: dt('fieldset.legend.border.radius');
        transition:
            background dt('fieldset.transition.duration'),
            color dt('fieldset.transition.duration'),
            outline-color dt('fieldset.transition.duration'),
            box-shadow dt('fieldset.transition.duration');
        outline-color: transparent;
    }

    .p-fieldset-legend-label {
        font-weight: dt('fieldset.legend.font.weight');
    }

    .p-fieldset-toggle-button:focus-visible {
        box-shadow: dt('fieldset.legend.focus.ring.shadow');
        outline: dt('fieldset.legend.focus.ring.width') dt('fieldset.legend.focus.ring.style') dt('fieldset.legend.focus.ring.color');
        outline-offset: dt('fieldset.legend.focus.ring.offset');
    }

    .p-fieldset-toggleable > .p-fieldset-legend:hover {
        color: dt('fieldset.legend.hover.color');
        background: dt('fieldset.legend.hover.background');
    }

    .p-fieldset-toggle-icon {
        color: dt('fieldset.toggle.icon.color');
        transition: color dt('fieldset.transition.duration');
    }

    .p-fieldset-toggleable > .p-fieldset-legend:hover .p-fieldset-toggle-icon {
        color: dt('fieldset.toggle.icon.hover.color');
    }

    .p-fieldset .p-fieldset-content {
        padding: dt('fieldset.content.padding');
    }
`,Re={root:function(e){var n=e.props;return["p-fieldset p-component",{"p-fieldset-toggleable":n.toggleable}]},legend:"p-fieldset-legend",legendLabel:"p-fieldset-legend-label",toggleButton:"p-fieldset-toggle-button",toggleIcon:"p-fieldset-toggle-icon",contentContainer:"p-fieldset-content-container",content:"p-fieldset-content"},He=U.extend({name:"fieldset",style:je,classes:Re}),Ne={name:"BaseFieldset",extends:R,props:{legend:String,toggleable:Boolean,collapsed:Boolean,toggleButtonProps:{type:null,default:null}},style:He,provide:function(){return{$pcFieldset:this,$parentInstance:this}}},oe={name:"Fieldset",extends:Ne,inheritAttrs:!1,emits:["update:collapsed","toggle"],data:function(){return{d_collapsed:this.collapsed}},watch:{collapsed:function(e){this.d_collapsed=e}},methods:{toggle:function(e){this.d_collapsed=!this.d_collapsed,this.$emit("update:collapsed",this.d_collapsed),this.$emit("toggle",{originalEvent:e,value:this.d_collapsed})},onKeyDown:function(e){(e.code==="Enter"||e.code==="NumpadEnter"||e.code==="Space")&&(this.toggle(e),e.preventDefault())}},computed:{buttonAriaLabel:function(){return this.toggleButtonProps&&this.toggleButtonProps.ariaLabel?this.toggleButtonProps.ariaLabel:this.legend},dataP:function(){return fe({toggleable:this.toggleable})}},directives:{ripple:ie},components:{PlusIcon:Me,MinusIcon:Se}};function V(t){"@babel/helpers - typeof";return V=typeof Symbol=="function"&&typeof Symbol.iterator=="symbol"?function(e){return typeof e}:function(e){return e&&typeof Symbol=="function"&&e.constructor===Symbol&&e!==Symbol.prototype?"symbol":typeof e},V(t)}function ee(t,e){var n=Object.keys(t);if(Object.getOwnPropertySymbols){var s=Object.getOwnPropertySymbols(t);e&&(s=s.filter(function(o){return Object.getOwnPropertyDescriptor(t,o).enumerable})),n.push.apply(n,s)}return n}function te(t){for(var e=1;e<arguments.length;e++){var n=arguments[e]!=null?arguments[e]:{};e%2?ee(Object(n),!0).forEach(function(s){Ge(t,s,n[s])}):Object.getOwnPropertyDescriptors?Object.defineProperties(t,Object.getOwnPropertyDescriptors(n)):ee(Object(n)).forEach(function(s){Object.defineProperty(t,s,Object.getOwnPropertyDescriptor(n,s))})}return t}function Ge(t,e,n){return(e=Ze(e))in t?Object.defineProperty(t,e,{value:n,enumerable:!0,configurable:!0,writable:!0}):t[e]=n,t}function Ze(t){var e=$e(t,"string");return V(e)=="symbol"?e:e+""}function $e(t,e){if(V(t)!="object"||!t)return t;var n=t[Symbol.toPrimitive];if(n!==void 0){var s=n.call(t,e);if(V(s)!="object")return s;throw new TypeError("@@toPrimitive must return a primitive value.")}return(e==="string"?String:Number)(t)}var Ue=["data-p"],qe=["data-p"],We=["id"],Ye=["id","aria-controls","aria-expanded","aria-label"],Je=["id","aria-labelledby"];function Qe(t,e,n,s,o,i){var f=ne("ripple");return l(),p("fieldset",u({class:t.cx("root"),"data-p":i.dataP},t.ptmi("root")),[d("legend",u({class:t.cx("legend"),"data-p":i.dataP},t.ptm("legend")),[P(t.$slots,"legend",{toggleCallback:i.toggle},function(){return[t.toggleable?I("",!0):(l(),p("span",u({key:0,id:t.$id+"_header",class:t.cx("legendLabel")},t.ptm("legendLabel")),w(t.legend),17,We)),t.toggleable?T((l(),p("button",u({key:1,id:t.$id+"_header",type:"button","aria-controls":t.$id+"_content","aria-expanded":!o.d_collapsed,"aria-label":i.buttonAriaLabel,class:t.cx("toggleButton"),onClick:e[0]||(e[0]=function(){return i.toggle&&i.toggle.apply(i,arguments)}),onKeydown:e[1]||(e[1]=function(){return i.onKeyDown&&i.onKeyDown.apply(i,arguments)})},te(te({},t.toggleButtonProps),t.ptm("toggleButton"))),[P(t.$slots,t.$slots.toggleicon?"toggleicon":"togglericon",{collapsed:o.d_collapsed,class:C(t.cx("toggleIcon"))},function(){return[(l(),y(A(o.d_collapsed?"PlusIcon":"MinusIcon"),u({class:t.cx("toggleIcon")},t.ptm("toggleIcon")),null,16,["class"]))]}),d("span",u({class:t.cx("legendLabel")},t.ptm("legendLabel")),w(t.legend),17)],16,Ye)),[[f]]):I("",!0)]})],16,qe),k(q,u({name:"p-toggleable-content"},t.ptm("transition")),{default:g(function(){return[T(d("div",u({id:t.$id+"_content",class:t.cx("contentContainer"),role:"region","aria-labelledby":t.$id+"_header"},t.ptm("contentContainer")),[d("div",u({class:t.cx("content")},t.ptm("content")),[P(t.$slots,"default")],16)],16,Je),[[me,!o.d_collapsed]])]}),_:3},16)],16,Ue)}oe.render=Qe;var Xe=`
    .p-tieredmenu {
        background: dt('tieredmenu.background');
        color: dt('tieredmenu.color');
        border: 1px solid dt('tieredmenu.border.color');
        border-radius: dt('tieredmenu.border.radius');
        min-width: 12.5rem;
    }

    .p-tieredmenu-root-list,
    .p-tieredmenu-submenu {
        margin: 0;
        padding: dt('tieredmenu.list.padding');
        list-style: none;
        outline: 0 none;
        display: flex;
        flex-direction: column;
        gap: dt('tieredmenu.list.gap');
    }

    .p-tieredmenu-submenu {
        position: absolute;
        min-width: 100%;
        z-index: 1;
        background: dt('tieredmenu.background');
        color: dt('tieredmenu.color');
        border: 1px solid dt('tieredmenu.border.color');
        border-radius: dt('tieredmenu.border.radius');
        box-shadow: dt('tieredmenu.shadow');
    }

    .p-tieredmenu-item {
        position: relative;
    }

    .p-tieredmenu-item-content {
        transition:
            background dt('tieredmenu.transition.duration'),
            color dt('tieredmenu.transition.duration');
        border-radius: dt('tieredmenu.item.border.radius');
        color: dt('tieredmenu.item.color');
    }

    .p-tieredmenu-item-link {
        cursor: pointer;
        display: flex;
        align-items: center;
        text-decoration: none;
        overflow: hidden;
        position: relative;
        color: inherit;
        padding: dt('tieredmenu.item.padding');
        gap: dt('tieredmenu.item.gap');
        user-select: none;
        outline: 0 none;
    }

    .p-tieredmenu-item-label {
        line-height: 1;
    }

    .p-tieredmenu-item-icon {
        color: dt('tieredmenu.item.icon.color');
    }

    .p-tieredmenu-submenu-icon {
        color: dt('tieredmenu.submenu.icon.color');
        margin-left: auto;
        font-size: dt('tieredmenu.submenu.icon.size');
        width: dt('tieredmenu.submenu.icon.size');
        height: dt('tieredmenu.submenu.icon.size');
    }

    .p-tieredmenu-submenu-icon:dir(rtl) {
        margin-left: 0;
        margin-right: auto;
    }

    .p-tieredmenu-item.p-focus > .p-tieredmenu-item-content {
        color: dt('tieredmenu.item.focus.color');
        background: dt('tieredmenu.item.focus.background');
    }

    .p-tieredmenu-item.p-focus > .p-tieredmenu-item-content .p-tieredmenu-item-icon {
        color: dt('tieredmenu.item.icon.focus.color');
    }

    .p-tieredmenu-item.p-focus > .p-tieredmenu-item-content .p-tieredmenu-submenu-icon {
        color: dt('tieredmenu.submenu.icon.focus.color');
    }

    .p-tieredmenu-item:not(.p-disabled) > .p-tieredmenu-item-content:hover {
        color: dt('tieredmenu.item.focus.color');
        background: dt('tieredmenu.item.focus.background');
    }

    .p-tieredmenu-item:not(.p-disabled) > .p-tieredmenu-item-content:hover .p-tieredmenu-item-icon {
        color: dt('tieredmenu.item.icon.focus.color');
    }

    .p-tieredmenu-item:not(.p-disabled) > .p-tieredmenu-item-content:hover .p-tieredmenu-submenu-icon {
        color: dt('tieredmenu.submenu.icon.focus.color');
    }

    .p-tieredmenu-item-active > .p-tieredmenu-item-content {
        color: dt('tieredmenu.item.active.color');
        background: dt('tieredmenu.item.active.background');
    }

    .p-tieredmenu-item-active > .p-tieredmenu-item-content .p-tieredmenu-item-icon {
        color: dt('tieredmenu.item.icon.active.color');
    }

    .p-tieredmenu-item-active > .p-tieredmenu-item-content .p-tieredmenu-submenu-icon {
        color: dt('tieredmenu.submenu.icon.active.color');
    }

    .p-tieredmenu-separator {
        border-block-start: 1px solid dt('tieredmenu.separator.border.color');
    }

    .p-tieredmenu-overlay {
        box-shadow: dt('tieredmenu.shadow');
    }

    .p-tieredmenu-enter-from,
    .p-tieredmenu-leave-active {
        opacity: 0;
    }

    .p-tieredmenu-enter-active {
        transition: opacity 250ms;
    }

    .p-tieredmenu-mobile .p-tieredmenu-submenu {
        position: static;
        box-shadow: none;
        border: 0 none;
        padding-inline-start: dt('tieredmenu.submenu.mobile.indent');
        padding-inline-end: 0;
    }

    .p-tieredmenu-mobile .p-tieredmenu-submenu:dir(rtl) {
        padding-inline-start: 0;
        padding-inline-end: dt('tieredmenu.submenu.mobile.indent');
    }

    .p-tieredmenu-mobile .p-tieredmenu-submenu-icon {
        transition: transform 0.2s;
        transform: rotate(90deg);
    }

    .p-tieredmenu-mobile .p-tieredmenu-item-active > .p-tieredmenu-item-content .p-tieredmenu-submenu-icon {
        transform: rotate(-90deg);
    }
`,et={submenu:function(e){var n=e.instance,s=e.processedItem;return{display:n.isItemActive(s)?"flex":"none"}}},tt={root:function(e){var n=e.props,s=e.instance;return["p-tieredmenu p-component",{"p-tieredmenu-overlay":n.popup,"p-tieredmenu-mobile":s.queryMatches}]},start:"p-tieredmenu-start",rootList:"p-tieredmenu-root-list",item:function(e){var n=e.instance,s=e.processedItem;return["p-tieredmenu-item",{"p-tieredmenu-item-active":n.isItemActive(s),"p-focus":n.isItemFocused(s),"p-disabled":n.isItemDisabled(s)}]},itemContent:"p-tieredmenu-item-content",itemLink:"p-tieredmenu-item-link",itemIcon:"p-tieredmenu-item-icon",itemLabel:"p-tieredmenu-item-label",submenuIcon:"p-tieredmenu-submenu-icon",submenu:"p-tieredmenu-submenu",separator:"p-tieredmenu-separator",end:"p-tieredmenu-end"},nt=U.extend({name:"tieredmenu",style:Xe,classes:tt,inlineStyles:et}),it={name:"BaseTieredMenu",extends:R,props:{popup:{type:Boolean,default:!1},model:{type:Array,default:null},appendTo:{type:[String,Object],default:"body"},breakpoint:{type:String,default:"960px"},autoZIndex:{type:Boolean,default:!0},baseZIndex:{type:Number,default:0},disabled:{type:Boolean,default:!1},tabindex:{type:Number,default:0},ariaLabelledby:{type:String,default:null},ariaLabel:{type:String,default:null}},style:nt,provide:function(){return{$pcTieredMenu:this,$parentInstance:this}}},ae={name:"TieredMenuSub",hostName:"TieredMenu",extends:R,emits:["item-click","item-mouseenter","item-mousemove"],container:null,props:{menuId:{type:String,default:null},focusedItemId:{type:String,default:null},items:{type:Array,default:null},visible:{type:Boolean,default:!1},level:{type:Number,default:0},templates:{type:Object,default:null},activeItemPath:{type:Object,default:null},tabindex:{type:Number,default:0}},methods:{getItemId:function(e){return"".concat(this.menuId,"_").concat(e.key)},getItemKey:function(e){return this.getItemId(e)},getItemProp:function(e,n,s){return e&&e.item?re(e.item[n],s):void 0},getItemLabel:function(e){return this.getItemProp(e,"label")},getItemLabelId:function(e){return"".concat(this.menuId,"_").concat(e.key,"_label")},getPTOptions:function(e,n,s){return this.ptm(s,{context:{item:e.item,index:n,active:this.isItemActive(e),focused:this.isItemFocused(e),disabled:this.isItemDisabled(e)}})},isItemActive:function(e){return this.activeItemPath.some(function(n){return n.key===e.key})},isItemVisible:function(e){return this.getItemProp(e,"visible")!==!1},isItemDisabled:function(e){return this.getItemProp(e,"disabled")},isItemFocused:function(e){return this.focusedItemId===this.getItemId(e)},isItemGroup:function(e){return B(e.items)},onEnter:function(){he(this.container,this.level)},onItemClick:function(e,n){this.getItemProp(n,"command",{originalEvent:e,item:n.item}),this.$emit("item-click",{originalEvent:e,processedItem:n,isFocus:!0})},onItemMouseEnter:function(e,n){this.$emit("item-mouseenter",{originalEvent:e,processedItem:n})},onItemMouseMove:function(e,n){this.$emit("item-mousemove",{originalEvent:e,processedItem:n})},getAriaSetSize:function(){var e=this;return this.items.filter(function(n){return e.isItemVisible(n)&&!e.getItemProp(n,"separator")}).length},getAriaPosInset:function(e){var n=this;return e-this.items.slice(0,e).filter(function(s){return n.isItemVisible(s)&&n.getItemProp(s,"separator")}).length+1},getMenuItemProps:function(e,n){return{action:u({class:this.cx("itemLink"),tabindex:-1},this.getPTOptions(e,n,"itemLink")),icon:u({class:[this.cx("itemIcon"),this.getItemProp(e,"icon")]},this.getPTOptions(e,n,"itemIcon")),label:u({class:this.cx("itemLabel")},this.getPTOptions(e,n,"itemLabel")),submenuicon:u({class:this.cx("submenuIcon")},this.getPTOptions(e,n,"submenuIcon"))}},containerRef:function(e){this.container=e}},components:{AngleRightIcon:Ke},directives:{ripple:ie}},st=["tabindex"],rt=["id","aria-label","aria-disabled","aria-expanded","aria-haspopup","aria-level","aria-setsize","aria-posinset","data-p-active","data-p-focused","data-p-disabled"],ot=["onClick","onMouseenter","onMousemove"],at=["href","target"],dt=["id"],lt=["id"];function ut(t,e,n,s,o,i){var f=O("AngleRightIcon"),v=O("TieredMenuSub",!0),c=ne("ripple");return l(),y(q,u({name:"p-tieredmenu",onEnter:i.onEnter},t.ptm("menu.transition")),{default:g(function(){return[n.level===0||n.visible?(l(),p("ul",{key:0,ref:i.containerRef,tabindex:n.tabindex},[(l(!0),p(F,null,se(n.items,function(r,h){return l(),p(F,{key:i.getItemKey(r)},[i.isItemVisible(r)&&!i.getItemProp(r,"separator")?(l(),p("li",u({key:0,id:i.getItemId(r),style:i.getItemProp(r,"style"),class:[t.cx("item",{processedItem:r}),i.getItemProp(r,"class")],role:"menuitem","aria-label":i.getItemLabel(r),"aria-disabled":i.isItemDisabled(r)||void 0,"aria-expanded":i.isItemGroup(r)?i.isItemActive(r):void 0,"aria-haspopup":i.isItemGroup(r)&&!i.getItemProp(r,"to")?"menu":void 0,"aria-level":n.level+1,"aria-setsize":i.getAriaSetSize(),"aria-posinset":i.getAriaPosInset(h)},{ref_for:!0},i.getPTOptions(r,h,"item"),{"data-p-active":i.isItemActive(r),"data-p-focused":i.isItemFocused(r),"data-p-disabled":i.isItemDisabled(r)}),[d("div",u({class:t.cx("itemContent"),onClick:function(a){return i.onItemClick(a,r)},onMouseenter:function(a){return i.onItemMouseEnter(a,r)},onMousemove:function(a){return i.onItemMouseMove(a,r)}},{ref_for:!0},i.getPTOptions(r,h,"itemContent")),[n.templates.item?(l(),y(A(n.templates.item),{key:1,item:r.item,hasSubmenu:i.getItemProp(r,"items"),label:i.getItemLabel(r),props:i.getMenuItemProps(r,h)},null,8,["item","hasSubmenu","label","props"])):T((l(),p("a",u({key:0,href:i.getItemProp(r,"url"),class:t.cx("itemLink"),target:i.getItemProp(r,"target"),tabindex:"-1"},{ref_for:!0},i.getPTOptions(r,h,"itemLink")),[n.templates.itemicon?(l(),y(A(n.templates.itemicon),{key:0,item:r.item,class:C(t.cx("itemIcon"))},null,8,["item","class"])):i.getItemProp(r,"icon")?(l(),p("span",u({key:1,class:[t.cx("itemIcon"),i.getItemProp(r,"icon")]},{ref_for:!0},i.getPTOptions(r,h,"itemIcon")),null,16)):I("",!0),d("span",u({id:i.getItemLabelId(r),class:t.cx("itemLabel")},{ref_for:!0},i.getPTOptions(r,h,"itemLabel")),w(i.getItemLabel(r)),17,dt),i.getItemProp(r,"items")?(l(),p(F,{key:2},[n.templates.submenuicon?(l(),y(A(n.templates.submenuicon),u({key:0,class:t.cx("submenuIcon"),active:i.isItemActive(r)},{ref_for:!0},i.getPTOptions(r,h,"submenuIcon")),null,16,["class","active"])):(l(),y(f,u({key:1,class:t.cx("submenuIcon")},{ref_for:!0},i.getPTOptions(r,h,"submenuIcon")),null,16,["class"]))],64)):I("",!0)],16,at)),[[c]])],16,ot),i.isItemVisible(r)&&i.isItemGroup(r)?(l(),y(v,u({key:0,id:i.getItemId(r)+"_list",class:t.cx("submenu"),style:t.sx("submenu",!0,{processedItem:r}),"aria-labelledby":i.getItemLabelId(r),role:"menu",menuId:n.menuId,focusedItemId:n.focusedItemId,items:r.items,templates:n.templates,activeItemPath:n.activeItemPath,level:n.level+1,visible:i.isItemActive(r)&&i.isItemGroup(r),pt:t.pt,unstyled:t.unstyled,onItemClick:e[0]||(e[0]=function(m){return t.$emit("item-click",m)}),onItemMouseenter:e[1]||(e[1]=function(m){return t.$emit("item-mouseenter",m)}),onItemMousemove:e[2]||(e[2]=function(m){return t.$emit("item-mousemove",m)})},{ref_for:!0},t.ptm("submenu")),null,16,["id","class","style","aria-labelledby","menuId","focusedItemId","items","templates","activeItemPath","level","visible","pt","unstyled"])):I("",!0)],16,rt)):I("",!0),i.isItemVisible(r)&&i.getItemProp(r,"separator")?(l(),p("li",u({key:1,id:i.getItemId(r),style:i.getItemProp(r,"style"),class:[t.cx("separator"),i.getItemProp(r,"class")],role:"separator"},{ref_for:!0},t.ptm("separator")),null,16,lt)):I("",!0)],64)}),128))],8,st)):I("",!0)]}),_:1},16,["onEnter"])}ae.render=ut;var de={name:"TieredMenu",extends:it,inheritAttrs:!1,emits:["focus","blur","before-show","before-hide","hide","show"],outsideClickListener:null,matchMediaListener:null,scrollHandler:null,resizeListener:null,target:null,container:null,menubar:null,searchTimeout:null,searchValue:null,data:function(){return{focused:!1,focusedItemInfo:{index:-1,level:0,parentKey:""},activeItemPath:[],visible:!this.popup,submenuVisible:!1,dirty:!1,query:null,queryMatches:!1}},watch:{activeItemPath:function(e){this.popup||(B(e)?(this.bindOutsideClickListener(),this.bindResizeListener()):(this.unbindOutsideClickListener(),this.unbindResizeListener()))}},mounted:function(){this.bindMatchMediaListener()},beforeUnmount:function(){this.unbindOutsideClickListener(),this.unbindResizeListener(),this.unbindMatchMediaListener(),this.scrollHandler&&(this.scrollHandler.destroy(),this.scrollHandler=null),this.container&&this.autoZIndex&&$.clear(this.container),this.target=null,this.container=null},methods:{getItemProp:function(e,n){return e?re(e[n]):void 0},getItemLabel:function(e){return this.getItemProp(e,"label")},isItemDisabled:function(e){return this.getItemProp(e,"disabled")},isItemVisible:function(e){return this.getItemProp(e,"visible")!==!1},isItemGroup:function(e){return B(this.getItemProp(e,"items"))},isItemSeparator:function(e){return this.getItemProp(e,"separator")},getProccessedItemLabel:function(e){return e?this.getItemLabel(e.item):void 0},isProccessedItemGroup:function(e){return e&&B(e.items)},toggle:function(e){this.visible?this.hide(e,!0):this.show(e)},show:function(e,n){this.popup&&(this.$emit("before-show"),this.visible=!0,this.target=this.target||e.currentTarget,this.relatedTarget=e.relatedTarget||null),n&&K(this.menubar)},hide:function(e,n){this.popup&&(this.$emit("before-hide"),this.visible=!1),this.activeItemPath=[],this.focusedItemInfo={index:-1,level:0,parentKey:""},n&&K(this.relatedTarget||this.target||this.menubar),this.dirty=!1},onFocus:function(e){this.focused=!0,this.popup||(this.focusedItemInfo=this.focusedItemInfo.index!==-1?this.focusedItemInfo:{index:this.findFirstFocusedItemIndex(),level:0,parentKey:""}),this.$emit("focus",e)},onBlur:function(e){this.focused=!1,this.focusedItemInfo={index:-1,level:0,parentKey:""},this.searchValue="",this.dirty=!1,this.$emit("blur",e)},onKeyDown:function(e){if(this.disabled){e.preventDefault();return}var n=e.metaKey||e.ctrlKey;switch(e.code){case"ArrowDown":this.onArrowDownKey(e);break;case"ArrowUp":this.onArrowUpKey(e);break;case"ArrowLeft":this.onArrowLeftKey(e);break;case"ArrowRight":this.onArrowRightKey(e);break;case"Home":this.onHomeKey(e);break;case"End":this.onEndKey(e);break;case"Space":this.onSpaceKey(e);break;case"Enter":case"NumpadEnter":this.onEnterKey(e);break;case"Escape":this.onEscapeKey(e);break;case"Tab":this.onTabKey(e);break;case"PageDown":case"PageUp":case"Backspace":case"ShiftLeft":case"ShiftRight":break;default:!n&&ye(e.key)&&this.searchItems(e,e.key);break}},onItemChange:function(e,n){var s=e.processedItem,o=e.isFocus;if(!j(s)){var i=s.index,f=s.key,v=s.level,c=s.parentKey,r=s.items,h=B(r),m=this.activeItemPath.filter(function(a){return a.parentKey!==c&&a.parentKey!==f});h&&(m.push(s),this.submenuVisible=!0),this.focusedItemInfo={index:i,level:v,parentKey:c},h&&(this.dirty=!0),o&&K(this.menubar),!(n==="hover"&&this.queryMatches)&&(this.activeItemPath=m)}},onOverlayClick:function(e){Fe.emit("overlay-click",{originalEvent:e,target:this.target})},onItemClick:function(e){var n=e.originalEvent,s=e.processedItem,o=this.isProccessedItemGroup(s),i=j(s.parent),f=this.isSelected(s);if(f){var v=s.index,c=s.key,r=s.level,h=s.parentKey;this.activeItemPath=this.activeItemPath.filter(function(a){return c!==a.key&&c.startsWith(a.key)}),this.focusedItemInfo={index:v,level:r,parentKey:h},this.dirty=!i,K(this.menubar)}else if(o)this.onItemChange(e);else{var m=i?s:this.activeItemPath.find(function(a){return a.parentKey===""});this.hide(n),this.changeFocusedItemIndex(n,m?m.index:-1),K(this.menubar)}},onItemMouseEnter:function(e){this.dirty&&this.onItemChange(e,"hover")},onItemMouseMove:function(e){this.focused&&this.changeFocusedItemIndex(e,e.processedItem.index)},onArrowDownKey:function(e){var n=this.focusedItemInfo.index!==-1?this.findNextItemIndex(this.focusedItemInfo.index):this.findFirstFocusedItemIndex();this.changeFocusedItemIndex(e,n),e.preventDefault()},onArrowUpKey:function(e){if(e.altKey){if(this.focusedItemInfo.index!==-1){var n=this.visibleItems[this.focusedItemInfo.index],s=this.isProccessedItemGroup(n);!s&&this.onItemChange({originalEvent:e,processedItem:n})}this.popup&&this.hide(e,!0),e.preventDefault()}else{var o=this.focusedItemInfo.index!==-1?this.findPrevItemIndex(this.focusedItemInfo.index):this.findLastFocusedItemIndex();this.changeFocusedItemIndex(e,o),e.preventDefault()}},onArrowLeftKey:function(e){var n=this,s=this.visibleItems[this.focusedItemInfo.index],o=this.activeItemPath.find(function(f){return f.key===s.parentKey}),i=j(s.parent);i||(this.focusedItemInfo={index:-1,parentKey:o?o.parentKey:""},this.searchValue="",this.onArrowDownKey(e)),this.activeItemPath=this.activeItemPath.filter(function(f){return f.parentKey!==n.focusedItemInfo.parentKey}),e.preventDefault()},onArrowRightKey:function(e){var n=this.visibleItems[this.focusedItemInfo.index],s=this.isProccessedItemGroup(n);s&&(this.onItemChange({originalEvent:e,processedItem:n}),this.focusedItemInfo={index:-1,parentKey:n.key},this.searchValue="",this.onArrowDownKey(e)),e.preventDefault()},onHomeKey:function(e){this.changeFocusedItemIndex(e,this.findFirstItemIndex()),e.preventDefault()},onEndKey:function(e){this.changeFocusedItemIndex(e,this.findLastItemIndex()),e.preventDefault()},onEnterKey:function(e){if(this.focusedItemInfo.index!==-1){var n=G(this.menubar,'li[id="'.concat("".concat(this.focusedItemId),'"]')),s=n&&G(n,'[data-pc-section="itemlink"]');if(s?s.click():n&&n.click(),!this.popup){var o=this.visibleItems[this.focusedItemInfo.index],i=this.isProccessedItemGroup(o);!i&&(this.focusedItemInfo.index=this.findFirstFocusedItemIndex())}}e.preventDefault()},onSpaceKey:function(e){this.onEnterKey(e)},onEscapeKey:function(e){if(this.popup||this.focusedItemInfo.level!==0){var n=this.focusedItemInfo;this.hide(e,!1),this.focusedItemInfo={index:Number(n.parentKey.split("_")[0]),level:0,parentKey:""},this.popup&&K(this.target)}e.preventDefault()},onTabKey:function(e){if(this.focusedItemInfo.index!==-1){var n=this.visibleItems[this.focusedItemInfo.index],s=this.isProccessedItemGroup(n);!s&&this.onItemChange({originalEvent:e,processedItem:n})}this.hide()},onEnter:function(e){this.autoZIndex&&$.set("menu",e,this.baseZIndex+this.$primevue.config.zIndex.menu),ve(e,{position:"absolute",top:"0"}),this.alignOverlay(),K(this.menubar),this.scrollInView()},onAfterEnter:function(){this.bindOutsideClickListener(),this.bindScrollListener(),this.bindResizeListener(),this.$emit("show")},onLeave:function(){this.unbindOutsideClickListener(),this.unbindScrollListener(),this.unbindResizeListener(),this.$emit("hide"),this.container=null,this.dirty=!1},onAfterLeave:function(e){this.autoZIndex&&$.clear(e)},alignOverlay:function(){Ie(this.container,this.target);var e=Z(this.target);e>Z(this.container)&&(this.container.style.minWidth=Z(this.target)+"px")},bindOutsideClickListener:function(){var e=this;this.outsideClickListener||(this.outsideClickListener=function(n){var s=e.container&&!e.container.contains(n.target),o=e.popup?!(e.target&&(e.target===n.target||e.target.contains(n.target))):!0;s&&o&&e.hide()},document.addEventListener("click",this.outsideClickListener,!0))},unbindOutsideClickListener:function(){this.outsideClickListener&&(document.removeEventListener("click",this.outsideClickListener,!0),this.outsideClickListener=null)},bindScrollListener:function(){var e=this;this.scrollHandler||(this.scrollHandler=new ge(this.target,function(n){e.hide(n,!0)})),this.scrollHandler.bindScrollListener()},unbindScrollListener:function(){this.scrollHandler&&this.scrollHandler.unbindScrollListener()},bindResizeListener:function(){var e=this;this.resizeListener||(this.resizeListener=function(n){be()||e.hide(n,!0)},window.addEventListener("resize",this.resizeListener))},unbindResizeListener:function(){this.resizeListener&&(window.removeEventListener("resize",this.resizeListener),this.resizeListener=null)},bindMatchMediaListener:function(){var e=this;if(!this.matchMediaListener){var n=matchMedia("(max-width: ".concat(this.breakpoint,")"));this.query=n,this.queryMatches=n.matches,this.matchMediaListener=function(){e.queryMatches=n.matches},this.query.addEventListener("change",this.matchMediaListener)}},unbindMatchMediaListener:function(){this.matchMediaListener&&(this.query.removeEventListener("change",this.matchMediaListener),this.matchMediaListener=null)},isItemMatched:function(e){var n;return this.isValidItem(e)&&((n=this.getProccessedItemLabel(e))===null||n===void 0?void 0:n.toLocaleLowerCase().startsWith(this.searchValue.toLocaleLowerCase()))},isValidItem:function(e){return!!e&&!this.isItemDisabled(e.item)&&!this.isItemSeparator(e.item)&&this.isItemVisible(e.item)},isValidSelectedItem:function(e){return this.isValidItem(e)&&this.isSelected(e)},isSelected:function(e){return this.activeItemPath.some(function(n){return n.key===e.key})},findFirstItemIndex:function(){var e=this;return this.visibleItems.findIndex(function(n){return e.isValidItem(n)})},findLastItemIndex:function(){var e=this;return Y(this.visibleItems,function(n){return e.isValidItem(n)})},findNextItemIndex:function(e){var n=this,s=e<this.visibleItems.length-1?this.visibleItems.slice(e+1).findIndex(function(o){return n.isValidItem(o)}):-1;return s>-1?s+e+1:e},findPrevItemIndex:function(e){var n=this,s=e>0?Y(this.visibleItems.slice(0,e),function(o){return n.isValidItem(o)}):-1;return s>-1?s:e},findSelectedItemIndex:function(){var e=this;return this.visibleItems.findIndex(function(n){return e.isValidSelectedItem(n)})},findFirstFocusedItemIndex:function(){var e=this.findSelectedItemIndex();return e<0?this.findFirstItemIndex():e},findLastFocusedItemIndex:function(){var e=this.findSelectedItemIndex();return e<0?this.findLastItemIndex():e},searchItems:function(e,n){var s=this;this.searchValue=(this.searchValue||"")+n;var o=-1,i=!1;return this.focusedItemInfo.index!==-1?(o=this.visibleItems.slice(this.focusedItemInfo.index).findIndex(function(f){return s.isItemMatched(f)}),o=o===-1?this.visibleItems.slice(0,this.focusedItemInfo.index).findIndex(function(f){return s.isItemMatched(f)}):o+this.focusedItemInfo.index):o=this.visibleItems.findIndex(function(f){return s.isItemMatched(f)}),o!==-1&&(i=!0),o===-1&&this.focusedItemInfo.index===-1&&(o=this.findFirstFocusedItemIndex()),o!==-1&&this.changeFocusedItemIndex(e,o),this.searchTimeout&&clearTimeout(this.searchTimeout),this.searchTimeout=setTimeout(function(){s.searchValue="",s.searchTimeout=null},500),i},changeFocusedItemIndex:function(e,n){this.focusedItemInfo.index!==n&&(this.focusedItemInfo.index=n,this.scrollInView())},scrollInView:function(){var e=arguments.length>0&&arguments[0]!==void 0?arguments[0]:-1,n=e!==-1?"".concat(this.$id,"_").concat(e):this.focusedItemId,s=G(this.menubar,'li[id="'.concat(n,'"]'));s&&s.scrollIntoView&&s.scrollIntoView({block:"nearest",inline:"start"})},createProcessedItems:function(e){var n=this,s=arguments.length>1&&arguments[1]!==void 0?arguments[1]:0,o=arguments.length>2&&arguments[2]!==void 0?arguments[2]:{},i=arguments.length>3&&arguments[3]!==void 0?arguments[3]:"",f=[];return e&&e.forEach(function(v,c){var r=(i!==""?i+"_":"")+c,h={item:v,index:c,level:s,key:r,parent:o,parentKey:i};h.items=n.createProcessedItems(v.items,s+1,h,r),f.push(h)}),f},containerRef:function(e){this.container=e},menubarRef:function(e){this.menubar=e?e.$el:void 0}},computed:{processedItems:function(){return this.createProcessedItems(this.model||[])},visibleItems:function(){var e=this,n=this.activeItemPath.find(function(s){return s.key===e.focusedItemInfo.parentKey});return n?n.items:this.processedItems},focusedItemId:function(){return this.focusedItemInfo.index!==-1?"".concat(this.$id).concat(B(this.focusedItemInfo.parentKey)?"_"+this.focusedItemInfo.parentKey:"","_").concat(this.focusedItemInfo.index):null}},components:{TieredMenuSub:ae,Portal:pe}},ct=["id"];function mt(t,e,n,s,o,i){var f=O("TieredMenuSub"),v=O("Portal");return l(),y(v,{appendTo:t.appendTo,disabled:!t.popup},{default:g(function(){return[k(q,u({name:"p-connected-overlay",onEnter:i.onEnter,onAfterEnter:i.onAfterEnter,onLeave:i.onLeave,onAfterLeave:i.onAfterLeave},t.ptm("transition")),{default:g(function(){return[o.visible?(l(),p("div",u({key:0,ref:i.containerRef,id:t.$id,class:t.cx("root"),onClick:e[0]||(e[0]=function(){return i.onOverlayClick&&i.onOverlayClick.apply(i,arguments)})},t.ptmi("root")),[t.$slots.start?(l(),p("div",u({key:0,class:t.cx("start")},t.ptm("start")),[P(t.$slots,"start")],16)):I("",!0),k(f,u({ref:i.menubarRef,id:t.$id+"_list",class:t.cx("rootList"),tabindex:t.disabled?-1:t.tabindex,role:"menubar","aria-label":t.ariaLabel,"aria-labelledby":t.ariaLabelledby,"aria-disabled":t.disabled||void 0,"aria-orientation":"vertical","aria-activedescendant":o.focused?i.focusedItemId:void 0,menuId:t.$id,focusedItemId:o.focused?i.focusedItemId:void 0,items:i.processedItems,templates:t.$slots,activeItemPath:o.activeItemPath,level:0,visible:o.submenuVisible,pt:t.pt,unstyled:t.unstyled,onFocus:i.onFocus,onBlur:i.onBlur,onKeydown:i.onKeyDown,onItemClick:i.onItemClick,onItemMouseenter:i.onItemMouseEnter,onItemMousemove:i.onItemMouseMove},t.ptm("rootList")),null,16,["id","class","tabindex","aria-label","aria-labelledby","aria-disabled","aria-activedescendant","menuId","focusedItemId","items","templates","activeItemPath","visible","pt","unstyled","onFocus","onBlur","onKeydown","onItemClick","onItemMouseenter","onItemMousemove"]),t.$slots.end?(l(),p("div",u({key:1,class:t.cx("end")},t.ptm("end")),[P(t.$slots,"end")],16)):I("",!0)],16,ct)):I("",!0)]}),_:3},16,["onEnter","onAfterEnter","onLeave","onAfterLeave"])]}),_:3},8,["appendTo","disabled"])}de.render=mt;var ft=`
    .p-splitbutton {
        display: inline-flex;
        position: relative;
        border-radius: dt('splitbutton.border.radius');
    }

    .p-splitbutton-button.p-button {
        border-start-end-radius: 0;
        border-end-end-radius: 0;
        border-inline-end: 0 none;
    }

    .p-splitbutton-button.p-button:focus-visible,
    .p-splitbutton-dropdown.p-button:focus-visible {
        z-index: 1;
    }

    .p-splitbutton-button.p-button:not(:disabled):hover,
    .p-splitbutton-button.p-button:not(:disabled):active {
        border-inline-end: 0 none;
    }

    .p-splitbutton-dropdown.p-button {
        border-start-start-radius: 0;
        border-end-start-radius: 0;
    }

    .p-splitbutton .p-menu {
        min-width: 100%;
    }

    .p-splitbutton-fluid {
        display: flex;
    }

    .p-splitbutton-rounded .p-splitbutton-dropdown.p-button {
        border-start-end-radius: dt('splitbutton.rounded.border.radius');
        border-end-end-radius: dt('splitbutton.rounded.border.radius');
    }

    .p-splitbutton-rounded .p-splitbutton-button.p-button {
        border-start-start-radius: dt('splitbutton.rounded.border.radius');
        border-end-start-radius: dt('splitbutton.rounded.border.radius');
    }

    .p-splitbutton-raised {
        box-shadow: dt('splitbutton.raised.shadow');
    }
`,pt={root:function(e){var n=e.instance,s=e.props;return["p-splitbutton p-component",{"p-splitbutton-raised":s.raised,"p-splitbutton-rounded":s.rounded,"p-splitbutton-fluid":n.hasFluid}]},pcButton:"p-splitbutton-button",pcDropdown:"p-splitbutton-dropdown"},ht=U.extend({name:"splitbutton",style:ft,classes:pt}),bt={name:"BaseSplitButton",extends:R,props:{label:{type:String,default:null},icon:{type:String,default:null},model:{type:Array,default:null},autoZIndex:{type:Boolean,default:!0},baseZIndex:{type:Number,default:0},appendTo:{type:[String,Object],default:"body"},disabled:{type:Boolean,default:!1},fluid:{type:Boolean,default:null},class:{type:null,default:null},style:{type:null,default:null},buttonProps:{type:null,default:null},menuButtonProps:{type:null,default:null},menuButtonIcon:{type:String,default:void 0},dropdownIcon:{type:String,default:void 0},severity:{type:String,default:null},raised:{type:Boolean,default:!1},rounded:{type:Boolean,default:!1},text:{type:Boolean,default:!1},outlined:{type:Boolean,default:!1},size:{type:String,default:null},plain:{type:Boolean,default:!1}},style:ht,provide:function(){return{$pcSplitButton:this,$parentInstance:this}}},le={name:"SplitButton",extends:bt,inheritAttrs:!1,emits:["click"],inject:{$pcFluid:{default:null}},data:function(){return{isExpanded:!1}},mounted:function(){var e=this;this.$watch("$refs.menu.visible",function(n){e.isExpanded=n})},methods:{onDropdownButtonClick:function(e){e&&e.preventDefault(),this.$refs.menu.toggle({currentTarget:this.$el,relatedTarget:this.$refs.button.$el}),this.isExpanded=this.$refs.menu.visible},onDropdownKeydown:function(e){(e.code==="ArrowDown"||e.code==="ArrowUp")&&(this.onDropdownButtonClick(),e.preventDefault())},onDefaultButtonClick:function(e){this.isExpanded&&this.$refs.menu.hide(e),this.$emit("click",e)}},computed:{containerClass:function(){return[this.cx("root"),this.class]},hasFluid:function(){return j(this.fluid)?!!this.$pcFluid:this.fluid}},components:{PVSButton:Ve,PVSMenu:de,ChevronDownIcon:Ce}},gt=["data-p-severity"];function It(t,e,n,s,o,i){var f=O("PVSButton"),v=O("PVSMenu");return l(),p("div",u({class:i.containerClass,style:t.style},t.ptmi("root"),{"data-p-severity":t.severity}),[k(f,u({type:"button",class:t.cx("pcButton"),label:t.label,disabled:t.disabled,severity:t.severity,text:t.text,icon:t.icon,outlined:t.outlined,size:t.size,fluid:t.fluid,"aria-label":t.label,onClick:i.onDefaultButtonClick},t.buttonProps,{pt:t.ptm("pcButton"),unstyled:t.unstyled}),J({default:g(function(){return[P(t.$slots,"default")]}),_:2},[t.$slots.icon?{name:"icon",fn:g(function(c){return[P(t.$slots,"icon",{class:C(c.class)},function(){return[d("span",u({class:[t.icon,c.class]},t.ptm("pcButton").icon,{"data-pc-section":"buttonicon"}),null,16)]})]}),key:"0"}:void 0]),1040,["class","label","disabled","severity","text","icon","outlined","size","fluid","aria-label","onClick","pt","unstyled"]),k(f,u({ref:"button",type:"button",class:t.cx("pcDropdown"),disabled:t.disabled,"aria-haspopup":"true","aria-expanded":o.isExpanded,"aria-controls":t.$id+"_overlay",onClick:i.onDropdownButtonClick,onKeydown:i.onDropdownKeydown,severity:t.severity,text:t.text,outlined:t.outlined,size:t.size,unstyled:t.unstyled},t.menuButtonProps,{pt:t.ptm("pcDropdown")}),{icon:g(function(c){return[P(t.$slots,t.$slots.dropdownicon?"dropdownicon":"menubuttonicon",{class:C(c.class)},function(){return[(l(),y(A(t.menuButtonIcon||t.dropdownIcon?"span":"ChevronDownIcon"),u({class:[t.dropdownIcon||t.menuButtonIcon,c.class]},t.ptm("pcDropdown").icon,{"data-pc-section":"menubuttonicon"}),null,16,["class"]))]})]}),_:3},16,["class","disabled","aria-expanded","aria-controls","onClick","onKeydown","severity","text","outlined","size","unstyled","pt"]),k(v,{ref:"menu",id:t.$id+"_overlay",model:t.model,popup:!0,autoZIndex:t.autoZIndex,baseZIndex:t.baseZIndex,appendTo:t.appendTo,unstyled:t.unstyled,pt:t.ptm("pcMenu")},J({_:2},[t.$slots.menuitemicon?{name:"itemicon",fn:g(function(c){return[P(t.$slots,"menuitemicon",{item:c.item,class:C(c.class)})]}),key:"0"}:void 0,t.$slots.item?{name:"item",fn:g(function(c){return[P(t.$slots,"item",{item:c.item,hasSubmenu:c.hasSubmenu,label:c.label,props:c.props})]}),key:"1"}:void 0]),1032,["id","model","autoZIndex","baseZIndex","appendTo","unstyled","pt"])],16,gt)}le.render=It;const vt={class:"w-full min-h-screen flex flex-col"},yt={class:"flex-1"},kt={class:"px-5 py-3 space-y-1"},wt={class:"text-sm text-gray-500 dark:text-gray-300"},xt={class:"space-y-3 p-5"},Lt={key:0,class:"text-xs text-gray-500 dark:text-gray-300"},Pt={class:"grid grid-cols-1 md:grid-cols-2 gap-x-6 gap-y-4"},St={class:"space-y-3 text-gray-600 dark:text-gray-300"},Mt={key:0,class:"text-xs text-gray-500 dark:text-gray-300"},Kt={class:"flex items-center justify-between gap-4"},Ct={class:"flex items-center space-x-2 text-sm"},Dt={class:"pi pi-question-circle cursor-pointer"},Et={class:"flex items-center justify-between gap-4"},Bt={class:"flex items-center space-x-2 text-sm"},Tt={class:"pi pi-question-circle cursor-pointer"},Ot={class:"flex items-center justify-between gap-4"},At={key:0,class:"pi pi-spin pi-spinner text-sm"},Ft={class:"flex items-center justify-between gap-4"},Vt={key:0,class:"pi pi-spin pi-spinner text-sm"},_t={class:"py-2 text-center text-sm text-neutral-500 dark:text-neutral-400"},zt={class:"flex items-center justify-center"},jt={key:0,class:"fixed inset-0 bg-black/20 z-50 flex items-center justify-center"},Rt={class:"bg-white dark:bg-neutral-800 p-8 rounded-lg shadow-2xl flex flex-col items-center"},Zt=ke({__name:"data-center.page",setup(t){const e=we(),n=z([]),s=z(""),o=z(!1),i=z(!1),f=xe(()=>[{label:i.value?"更新全量数据":"更新增量数据",icon:"pi pi-refresh",command:()=>{i.value?r():h()}}]);Le(()=>{v(),c()});const v=async()=>{var a,S;const m=await De("config");if(m.result===!0)if((a=m.data)!=null&&a.pre_data_path){let D=(S=m.data)==null?void 0:S.pre_data_path;const H=D.includes("\\")?"\\":"/",_=D.lastIndexOf(H);s.value=_!==-1?D.substring(0,_):D}else s.value=""},c=async()=>{const m=await Ee();if(m.result===!0&&m.data)if(Object.keys(m.data).length>0){i.value=!0,n.value=Object.values(m.data);const a=n.value.find(S=>S.product_name==="coin-binance-spot-swap-preprocess-pkl-1h");a&&(n.value=[a,...n.value.filter(S=>S.product_name!=="coin-binance-spot-swap-preprocess-pkl-1h")])}else i.value=!1,n.value=[];else i.value=!1,n.value=[]},r=async()=>{o.value=!0;try{const m=await Be();m.result===!0&&(e.add({severity:"success",summary:`全量数据${m.data.join(",")}更新成功！`,life:3e3}),setTimeout(()=>{c()},2e3))}finally{o.value=!1}},h=async()=>{o.value=!0;try{(await Te()).result===!0&&(e.add({severity:"success",summary:"增量数据更新成功！",life:3e3}),setTimeout(()=>{c()},2e3))}finally{o.value=!1}};return(m,a)=>{var W;const S=_e,D=le,M=Ae,H=oe,_=ze,ue=Oe,N=Pe;return l(),p(F,null,[d("div",vt,[d("div",yt,[d("div",kt,[a[1]||(a[1]=d("h1",{class:"text-2xl font-semibold text-gray-800 dark:text-gray-100"}," 数据中心 ",-1)),d("span",wt,"数据存储地址："+w(s.value||"暂无"),1)]),k(S,{class:"m-0"}),d("div",xt,[T(k(D,{label:"更新数据",model:f.value,icon:"pi pi-refresh",onClick:a[0]||(a[0]=b=>i.value?h():r())},null,8,["model"]),[[N,{value:"第一次会全量更新"},void 0,{top:!0}]]),((W=n.value)==null?void 0:W.length)===0?(l(),p("div",Lt," 暂无数据更新记录，请点击「更新数据」按钮下载最新数据。 ")):I("",!0),d("div",Pt,[(l(!0),p(F,null,se(n.value,(b,ce)=>(l(),y(H,{key:ce},{legend:g(()=>[d("div",{class:C(["space-x-2 font-semibold",b.product_name==="coin-binance-spot-swap-preprocess-pkl-1h"?"text-primary-500":""])},[d("span",null,w(b.display_name||"暂无"),1),d("span",{class:C(["text-sm",b.product_name==="coin-binance-spot-swap-preprocess-pkl-1h"?"text-primary-500":"text-gray-500 dark:text-gray-300"])},"("+w(b.product_name||"暂无")+")",3)],2)]),default:g(()=>[d("div",St,[b.product_name==="coin-binance-spot-swap-preprocess-pkl-1h"?(l(),p("div",Mt," 基础数据下载完成后，系统将自动执行合并处理并生成预处理数据 ")):I("",!0),d("div",Kt,[d("div",Ct,[a[2]||(a[2]=d("div",{class:"w-1.5 h-1.5 rounded-full bg-gray-500 dark:bg-gray-300"},null,-1)),a[3]||(a[3]=d("span",{class:"font-semibold"}," 数据更新至",-1)),T(d("i",Dt,null,512),[[N,{value:"最新行情数据日期",autoHide:!1}]])]),k(M,{severity:"secondary",class:"text-xs font-medium"},{default:g(()=>[x(w(b.dataContentTime||"暂无"),1)]),_:2},1024)]),d("div",Et,[d("div",Bt,[a[4]||(a[4]=d("div",{class:"w-1.5 h-1.5 rounded-full bg-gray-500 dark:bg-gray-300"},null,-1)),a[5]||(a[5]=d("span",{class:"font-semibold"}," 数据更新时间",-1)),T(d("i",Tt,null,512),[[N,{value:"服务器最近上传数据的时间",autoHide:!1}]])]),k(M,{severity:"secondary",class:"text-xs font-medium"},{default:g(()=>[x(w(b.lastUpdateTime||"暂无"),1)]),_:2},1024)]),d("div",Ot,[a[7]||(a[7]=d("div",{class:"flex items-center space-x-2 text-sm"},[d("div",{class:"w-1.5 h-1.5 rounded-full bg-gray-500 dark:bg-gray-300"}),d("span",{class:"text-gray-600 dark:text-gray-300 font-semibold"}," 全量数据下载状态")],-1)),b.full_status?(l(),y(M,{key:0,severity:b.full_status===L(E).success?"success":b.full_status===L(E).downloading?"warning":"danger",class:"text-xs"},{default:g(()=>[b.full_status===L(E).downloading?(l(),p("i",At)):I("",!0),x(w(L(Q)[b.full_status]),1)]),_:2},1032,["severity"])):(l(),y(M,{key:1,severity:"secondary"},{default:g(()=>a[6]||(a[6]=[x("暂无")])),_:1,__:[6]}))]),d("div",Ft,[a[9]||(a[9]=d("div",{class:"flex items-center space-x-2 text-sm"},[d("div",{class:"w-1.5 h-1.5 rounded-full bg-gray-500 dark:bg-gray-300"}),d("span",{class:"text-gray-600 dark:text-gray-300 font-semibold"}," 增量数据下载状态")],-1)),b.update_status?(l(),y(M,{key:0,severity:b.update_status===L(E).success?"success":b.update_status===L(E).downloading?"warning":"danger",class:"text-xs"},{default:g(()=>[b.update_status===L(E).downloading?(l(),p("i",Vt)):I("",!0),x(w(L(Q)[b.update_status]),1)]),_:2},1032,["severity"])):(l(),y(M,{key:1,severity:"secondary"},{default:g(()=>a[8]||(a[8]=[x("暂无")])),_:1,__:[8]}))])])]),_:2},1024))),128))])])]),d("footer",_t,[d("div",zt,[x(w(L(X)==="coin"?"B圈回测网页版":"股票回测网页版")+" ",1),k(S,{layout:"vertical"}),a[10]||(a[10]=x(" 公测版本 ")),k(_,{severity:"secondary",size:"small",class:"h-6 font-mono mx-2"},{default:g(()=>[x(w(L(X)==="coin"?"v0.2.0":"v0.1.0"),1)]),_:1}),a[11]||(a[11]=x("© 2025 "))])])]),o.value?(l(),p("div",jt,[d("div",Rt,[k(ue,{class:"mb-4"}),a[12]||(a[12]=d("p",{class:"text-lg font-medium mb-2"},"数据更新中，请耐心等待...",-1)),a[13]||(a[13]=d("p",{class:"text-gray-500 dark:text-neutral-400 text-sm flex items-center gap-2"},[d("i",{class:"pi pi-exclamation-triangle text-yellow-600"}),x("数据更新期间请勿刷新页面或关闭浏览器 ")],-1))])])):I("",!0)],64)}}});export{Zt as default};
