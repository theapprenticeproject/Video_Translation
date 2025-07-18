// Copyright (c) 2025, VT and contributors
// For license information, please see license.txt

let original_price;
frappe.ui.form.on("Client Script Lab", {
    validate: function(frm){
        if (frm.doc.price>500){
            msgprint("This price is quite expensive")
            frappe.validated=false;
        }

        if (String(frm.doc.author).trim()===""){
            frm.set_value('author', "Anonymous")
        }

        if (frm.doc.category==="Science"){
            frm.doc.tags="Physics, Research"
        }

        if (frm.doc.title.toLowerCase().includes("test")){
            msgprint("Please remove the word 'test' from the title")
            frappe.validated=false
        }
    },

    refresh: function(frm){
        frm.add_custom_button(__('Show Summary'), function(){
            frappe.msgprint(`The article titled ${frm.doc.title} by ${frm.doc.author} falls under ${frm.doc.category} category and is priced at ₹${frm.doc.price}.`)
        })

        frm.add_custom_button("Copy Title", function(){
            navigator.clipboard.writeText(frm.doc.title)
        })

        frm.add_custom_button("Get Discounted Price", function(){
            // frappe.call({
            //     method: "my_app.self_app.doctype.client_script_lab.client_script_lab.get_discounted_price",
            //     args:{
            //         price: frm.doc.price
            //     },
            //     callback: function(r){
            //         msgprint(`The discounted price could be ${r.message} with a discount of 10%`)
            //         frm.set_value("price", r.message)
            //     }
            // })
            frm.trigger("get_discount_price")
        })

        
    },

    get_discount_price: (frm)=>{
        if (!original_price) {
            msgprint("Price not set, cannot apply discount")
            return;
        }
        frm.call({
            doc: frm.doc, 
            method: 'get_discounted_price',
            args:{
                price: original_price
            },
            callback: (r)=>{
                frm.set_value("price", r.message)
                msgprint(`A Discount of 10% is applied thus, ${r.message}`)
            }
        })
    },

    apply_discount: (frm)=>{
        if (frm.doc.apply_discount){
            frm.trigger("get_discount_price")
            if (!original_price) original_price=frm.doc.price
        }else{
            if (original_price){
                frm.set_value("price", original_price)
                msgprint("original price set")
            }
        }
    },

    author: function(frm){
        if (frm.doc.author==="Admin"){
            frappe.msgprint(__("Be warned, u are the admin"))
        }
    },

    category: function(frm){
        frm.toggle_display(["tags"], frm.doc.category==="Science");
    }
});
