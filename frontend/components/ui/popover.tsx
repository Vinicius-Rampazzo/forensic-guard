"use client"

import * as React from "react"
import { cn } from "cn"
import { Popover as PopoverPrimitive } from "radix-ui"

function Popover({ ...props }: React.ComponentProps<typeof PopoverPrimitive.Root>) {
  return <PopoverPrimitive.Root data-slot="popover" {...props} />
}

function PopoverTrigger({
  ...props
}: React.ComponentProps<typeof PopoverPrimitive.Trigger>) {
  return <PopoverPrimitive.Trigger data-slot="popover-trigger" {...props} />
}

function PopoverAnchor({
  ...props
}: React.ComponentProps<typeof PopoverPrimitive.Anchor>) {
  return <PopoverPrimitive.Anchor data-slot="popover-anchor" {...props} />
}

function PopoverContent({
  className,
  align = "center",
  sideOffset = 8,
  children,
  ...props
}: React.ComponentProps<typeof PopoverPrimitive.Content>) {
  return (
    <PopoverPrimitive.Portal>
      <PopoverPrimitive.Content
        data-slot="popover-content"
        align={align}
        sideOffset={sideOffset}
        className={cn(
          "z-50 w-72 origin-(--radix-popover-content-transform-origin) rounded-lg border bg-popover p-4 text-popover-foreground shadow-lg outline-hidden data-[side=bottom]:slide-in-from-top-2 data-[side=left]:slide-in-from-right-2 data-[side=right]:slide-in-from-left-2 data-[side=top]:slide-in-from-bottom-2 data-open:animate-in data-open:fade-in-0 data-open:zoom-in-95 data-closed:animate-out data-closed:fade-out-0 data-closed:zoom-out-95",
          className
        )}
        {...props}
      >
        {children}
        {/*
          A seta e um <svg> com um <polygon> dentro. O que a pinta e `fill`,
          nao `bg` - `bg-popover` colore a caixa do svg e deixa o poligono com
          o preto padrao, que foi o triangulo preto que aparecia aqui.

          Sem rotacao nem deslocamento manual: o proprio Radix orienta a seta
          conforme o lado em que o balao coube, entao ela sempre aponta para
          fora. Girar a mao so funciona enquanto o balao nao vira de lado.

          `fill-foreground` e uma escolha deliberada, e nao o padrao. O comum
          e a seta ter a cor do balao, como extensao dele. Aqui ela usa a cor
          do TEXTO - preta no tema claro, branca no escuro - porque o papel
          dela nao e emendar o balao, e apontar: estes balões sao de
          orientacao, e a seta funciona como a de uma anotacao.
        */}
        <PopoverPrimitive.Arrow width={14} height={7} className="fill-foreground" />
      </PopoverPrimitive.Content>
    </PopoverPrimitive.Portal>
  )
}

export { Popover, PopoverAnchor, PopoverContent, PopoverTrigger }
