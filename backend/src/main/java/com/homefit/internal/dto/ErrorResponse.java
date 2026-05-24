package com.homefit.internal.dto;

public record ErrorResponse(String code, String message, String detail) {
}
